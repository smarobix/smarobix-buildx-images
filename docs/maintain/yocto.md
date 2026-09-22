# Rebuild the Yocto images

[`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto) holds the Yocto/meta-ros configuration for the Kria K26 (KV260 and KR260) and the Raspberry Pi 5: kas files layered on meta-ros's own, and `meta-smrbx`, a small local layer. Four things are built from it:

| Output | What it is | Where it goes |
|---|---|---|
| `ros-image-core` | The board image | Not published; you flash it yourself |
| `ros2-image-sdktest -c populate_sdk` | The SDK installer that `dockerfiles/oesdk` packages | A GitHub Release asset, for CI to download |
| `ros-dev-container` | An aarch64 OCI image of the board's own userspace | Pushed to GHCR by hand |
| — | The `oe-sdk` cross images | Built in CI from the SDK installer, on the dev container |

The images are published, so you need this page only to rebuild them. The tags are listed in the [targets reference](../reference/targets.md). Results from running them on real boards are in [Tested hardware](../reference/tested-hardware.md).

```
yocto/
  kas/                  kas files, overlaid on meta-ros's own kas configs
    smrbx-shared.yml    shared settings for every machine (caches, SDK, SSH, meta-smrbx)
    machine/            one file per Kria starter kit
    oeros-scarthgap-jazzy-k26-smk-{kv,kr}-sdt.yml   top-level configs
  meta-smrbx/           local layer: OpenSSH fix, dev container image
```

## The build host

These builds were done on an arm64 Linux machine. Bitbake must not run as root, and the host had neither pip nor sudo, so kas ran inside an `ubuntu:24.04` container with the Yocto host packages installed, as a uid-1000 user matching the host's. `/work` in the paths below is that container's view of the host's build directory.

`smrbx-shared.yml` sets `BB_NUMBER_THREADS` and `PARALLEL_MAKE` to 12. Adjust both to the machine you build on.

## How the kas files fit together

These files are not standalone. The top-level configs include files from the **`build` branch of [meta-ros](https://github.com/ros/meta-ros/tree/build/kas)** (`kas/yocto/scarthgap.yml`, `kas/ros2/jazzy.yml`, `kas/common.yml`, `kas/layer/lts-mixins.yml`). meta-ros's kas set covers only qemu and Raspberry Pi machines, so the Kria machines are added here. The Raspberry Pi 5 uses meta-ros's own `kas/oeros-scarthgap-jazzy-raspberrypi5.yml`, with `smrbx-shared.yml` on top.

The commit these builds used:

```bash
git clone -b build https://github.com/ros/meta-ros.git meta-ros-build
git -C meta-ros-build checkout 4212d293d5779d3c3b8c445de15066e640d2e601
cp yocto/kas/*.yml         meta-ros-build/kas/
cp yocto/kas/machine/*.yml meta-ros-build/kas/machine/
# meta-smrbx is referenced by absolute path from smrbx-shared.yml, so copy it
# to the path that file names:
cp -r yocto/meta-smrbx /work/buildx-yocto/meta-smrbx
```

`smrbx-shared.yml` points at `/work/buildx-yocto/meta-smrbx`, `/work/downloads` and `/work/sstate`. Adjust those paths if you run kas differently.

## Build commands

For the KV260; swap `kv` for `kr` to get the KR260:

```bash
CFG=kas/oeros-scarthgap-jazzy-k26-smk-kv-sdt.yml:kas/smrbx-shared.yml
kas build $CFG                                                   # board image (ros-image-core)
kas shell $CFG -c 'bitbake ros2-image-sdktest -c populate_sdk'   # SDK installer
kas shell $CFG -c 'bitbake ros-dev-container'                    # OCI dev container
```

The Raspberry Pi 5 uses the same three commands with:

```bash
CFG=kas/oeros-scarthgap-jazzy-raspberrypi5.yml:kas/smrbx-shared.yml
```

## Why the machine files look the way they do

Each of these cost a failed build. They are commented inline too; don't tidy them away.

- **`k26-smk-kv-sdt` and `k26-smk-kr-sdt`, not `k26-smk-kv` and `k26-smk-kr`.** The plain machines set `XILINX_WITH_ESW = "xsct"`, and XSCT is an x86_64-only AMD binary. The SDT (system device tree) variants download prebuilt SDT artifacts and process them with lopper, which runs on any host.
- **meta-xilinx on `rel-v2025.2`, not `scarthgap`.** meta-kria `rel-v2025.2` inherits `amd_spi_image.bbclass`, which exists only on meta-xilinx's `rel-v*` branches. That branch still declares `LAYERSERIES_COMPAT = "scarthgap"`, so it stays compatible with the poky commit meta-ros pins. Both land on tag `amd-edf-rel-v25.11.1`, and all four Xilinx-side repositories are pinned to exact commits.
- **`meta-xilinx-multimedia` is included.** The machines set `MACHINE_HWCODECS = "libvcu-omxil"` and add the `hwcodecs` image feature, so without that layer the image fails with `Nothing RPROVIDES 'libvcu-omxil'`.
- **`FSBL_DEPLOY_DIR:forcevariable` and `PMU_FIRMWARE_DEPLOY_DIR:forcevariable`.** meta-ros's `ros2` distro builds into `tmp-glibc`, while the firmware multiconfigs (`DISTRO = "xilinx-standalone"`) build into `tmp-<mc>`. The machine conf derives the firmware location from the consumer's `TMPDIR`, so it looks in `tmp-glibc-<mc>` and FSBL and PMU firmware fail at the very end of the build. `:forcevariable` is required, because `machine.conf` is parsed after `local.conf` and assigns these with a plain `=`.

## What `smrbx-shared.yml` adds

- Shared `DL_DIR` and `SSTATE_DIR` across machines, and `wic.bz2` and `wic.bmap` outputs.
- **`TOOLCHAIN_HOST_TASK:append = " nativesdk-ros-sdk-env"`.** `ros-sdk-env` is what sets `OE_CMAKE_TOOLCHAIN_FILE`, derives `PYTHON_SOABI` and sets `AMENT_PREFIX_PATH` in the SDK, and nothing in meta-ros references it: not `ROS_SDK_HOST_PACKAGES`, not any image. Without this line the SDK cannot configure a ROS workspace. Build the SDK from `ros2-image-sdktest`; `ros-image-core -c populate_sdk` also lacks colcon.
- **`ssh-server-openssh` and `rsync`** in the images, so a workspace can be deployed over SSH. OpenSSH rather than dropbear: modern `scp` uses SFTP, which dropbear lacks.
- **`SDKIMAGE_FEATURES = "dev-pkgs"`.** The SDK is for building against, not for debugging on. With the default `dev-pkgs dbg-pkgs src-pkgs`, debug symbols made up 72 % of the KV260 SDK's target sysroot and debug sources another 8 %. Dropping them shrank the installer from 1.1 GB to 272 MB. See [Tested hardware](../reference/tested-hardware.md#image-sizes) for the published sizes.

## meta-smrbx

- **`recipes-connectivity/openssh/openssh_%.bbappend`** appends `IPQoS none` to `sshd_config`. On the KV260, interactive SSH died after about 18 seconds with "Broken pipe" while commands without a terminal worked. With a PTY, OpenSSH switches its packets to an interactive DSCP marking, and the board's marked replies were lost on the way to the LAN. Server-side `IPQoS none` fixes it; client-side does not.
- **`recipes-core/images/ros-dev-container.bb`** builds the dev container, below.

## The dev container

An aarch64 OCI image of the meta-ros userspace with compilers and `-dev` packages, built from **the same configuration as the board image**. colcon-buildx builds in it natively, through its normal Docker path for images that run as the target architecture, so a workspace is compiled against exactly the libraries the board ships. There is no Ubuntu base and no cross toolchain. It carries the label `org.smarobix.buildx.kind=yocto-native`, together with `ros-distro` and `target-platform`; see the [image label contract](https://smarobix.github.io/smarobix-buildx-images/tool/reference/labels/).

Every choice in `ros-dev-container.bb` was prompted by a failure:

- `IMAGE_FSTYPES:remove = "wic.bz2 wic.bmap"`: `smrbx-shared.yml` appends those for the board images, and an `:append` lands after the recipe's own `IMAGE_FSTYPES = "oci"`, so without this bitbake also writes a useless disk image of the container's rootfs.
- `inherit image-container image-oci`: the `oci` image type depends on OE-core's `container` type. `IMAGE_CONTAINER_NO_DUMMY = "1"` opts out of `image-container`'s demand for a `linux-dummy` kernel; the container installs no kernel, and the board image built from the same configuration needs the real one.
- `OCI_IMAGE_ENTRYPOINT = ""`: the default entrypoint `sh` would turn colcon-buildx's `bash -c '…'` into `sh bash -c …`.
- No `packagegroup-core-boot`, because a container needs no init system. That also means no busybox, so `sed grep gawk tar gzip which` are listed explicitly.
- `xz`: `dockerfiles/oesdk` builds the SDK image on top of this container, and the SDK installer's payload is xz-compressed.
- `python-cmake-module`: `rosidl_generator_py` `find_package()`s it, and every interface package fails to configure without it. Unlike the SDK, this container has the Python message generator, so interface packages get Python bindings too.
- `OCI_IMAGE_ENV_VARS = "LDFLAGS=-Wl,-O1,--hash-style=gnu,--as-needed"`: link the way the distro does. `rcutils` exports `-latomic` to every package that uses it. OE builds and the SDK link with `--as-needed`, so the unused library is dropped. Without these flags the container kept it as a hard dependency and the binary then failed on the board with `libatomic.so.1: cannot open shared object file`, because the board does not ship libatomic. It is written as one token because `OCI_IMAGE_ENV_VARS` is space-separated.
- `IMAGE_FEATURES += "tools-sdk dev-pkgs"`: target compilers, plus the headers and CMake configs of everything installed.

### Load one you built yourself

Loading needs `skopeo`. Bitbake's OCI archive records only the tag (`jazzy`) as its reference name and no platform, so a plain `docker load` leaves an image Docker cannot resolve by name. `skopeo` converts it into a Docker archive with an explicit name:

```bash
D=/work/buildx-yocto/build/tmp-glibc/deploy/images/k26-smk-kv-sdt
docker run --rm --user $(id -u):$(id -g) -v "$D:/in:ro" -v /tmp:/out quay.io/skopeo/stable \
  copy oci-archive:/in/ros-dev-container-jazzy-jazzy-oci.tar:jazzy \
       docker-archive:/out/devctr.tar:ros-dev-container:jazzy
docker load -i /tmp/devctr.tar

colcon buildx --method docker --docker-image ros-dev-container:jazzy --docker-platform linux/arm64
```

`D` is the deploy directory of your build: `<build dir>/tmp-glibc/deploy/images/<machine>`.

### Publish the dev container

CI cannot build these, and a CI job that reached into a build host's Yocto downloads and sstate would not be reproducible, so they are pushed by hand. Load the image as above, then push it with a throwaway Docker configuration, so the registry token never lands in `~/.docker`:

```bash
docker tag ros-dev-container:jazzy \
  ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy

export DOCKER_CONFIG=$(mktemp -d)
# a GitHub token with the write:packages scope, and your GitHub user name
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
docker push ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy
docker logout ghcr.io
rm -rf "$DOCKER_CONFIG"
unset DOCKER_CONFIG
```

The SDK images build `FROM` this tag, so start a build on `main` afterwards to rebuild them; see [CI and releases](ci-and-releases.md#the-hand-pushed-yocto-dev-containers).

## The SDK

The SDK installer is what `dockerfiles/oesdk` turns into the `oe-sdk` cross images. Three properties of it matter:

- **It must contain `ros-sdk-env`**, which is what `smrbx-shared.yml` adds. Build it from `ros2-image-sdktest`.
- **It is `linux/arm64` only.** The SDK's host tools are aarch64 binaries, so the image runs natively on Apple Silicon and on arm64 Linux. An x86_64 variant needs a second SDK built with `SDKMACHINE = "x86_64"`, on an x86_64 base image.
- **It has no Python message bindings.** There is no `rosidl_generator_py` in it, so interface packages get C and C++ bindings only. The dev container generates the Python ones. The SDK also ships `ninja` but not `make`, so colcon-buildx builds with ninja.

To build the image yourself, pass the directory holding the installer as the `sdk` build context. It is bind-mounted during the build, so the installer never ends up in a layer:

```bash
docker buildx build --platform linux/arm64 --load \
  --build-context sdk=/path/to/installer/dir \
  --build-arg BASE_IMAGE=ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy \
  --build-arg SDK_INSTALLER=oecore-ros2-image-sdktest-jazzy-aarch64-cortexa72-cortexa53-k26-smk-kv-sdt-toolchain-nodistro.0.sh \
  --build-arg SDK_ENV_SETUP=environment-setup-cortexa72-cortexa53-oe-linux \
  -t buildx-local:k26-oesdk-jazzy dockerfiles/oesdk
```

`SDK_ENV_SETUP` names the SDK's environment script, which follows the target CPU tune: `cortexa72-cortexa53` for the Kria K26, `cortexa76` for the Raspberry Pi 5 (with `rpi5-yocto-jazzy` as the base image). The labels colcon-buildx reads are derived from it.

Publishing a new SDK, and updating the `oe-sdk` entries in `targets.yml` to its release tag and checksums, is described in [CI and releases](ci-and-releases.md#sdk-releases).

## The board image

`ros-image-core` is `ros-core` only, which includes `rclcpp`, and no demo nodes. It is not published; flash it yourself. On the board:

- Log in as `root` with an empty password, over the serial console or SSH. Bench use only.
- There is **no bash**, only BusyBox ash: source `/opt/ros/jazzy/setup.sh`, not `setup.bash`. BusyBox here has no `timeout` and supports only `head -n N`, so write board-side scripts accordingly.
- The NIC is `end0`, with DHCP through systemd-networkd or connman.
- Flash the image that matches the carrier. U-Boot prints `SCK-KV-G` or `SCK-KR-G` at boot. Boot from SD; don't write `boot.bin` to QSPI unless the card will not boot.
