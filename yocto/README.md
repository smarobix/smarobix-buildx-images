# Yocto / meta-ros builds for the Kria K26 and Raspberry Pi 5

The configuration behind the Yocto side of this repository: the board images for
the KV260, KR260 and Raspberry Pi 5, the meta-ros SDKs that `dockerfiles/oesdk`
packages, and a small local layer. Everything here was built and tested on an arm64
Linux host (`smrbx-thor-0`) in September 2026.

The images built from it are published, so you only need this to rebuild them:

| Board | SDK image | Dev container |
|---|---|---|
| Kria K26 (KV260 / KR260) | `k26-oesdk-jazzy` | `k26-yocto-jazzy` |
| Raspberry Pi 5 | `rpi5-oesdk-jazzy` | `rpi5-yocto-jazzy` |

All under `ghcr.io/smarobix/smarobix-buildx-images`.

```
yocto/
  kas/                  kas files, overlaid on meta-ros's own kas configs
    smrbx-shared.yml    shared settings for every machine (caches, SDK, SSH, meta-smrbx)
    machine/            one file per Kria starter kit
    oeros-scarthgap-jazzy-k26-smk-{kv,kr}-sdt.yml   top-level configs
  meta-smrbx/           local layer: OpenSSH fix, dev container image
```

## How the kas files fit together

These files are not standalone. The top-level configs include files from the
**`build` branch of [meta-ros](https://github.com/ros/meta-ros/tree/build/kas)**
(`kas/yocto/scarthgap.yml`, `kas/ros2/jazzy.yml`, `kas/common.yml`,
`kas/layer/lts-mixins.yml`). meta-ros's kas set covers only qemu and Raspberry Pi, so
the Kria machines are added here. The Raspberry Pi 5 uses meta-ros's own
`kas/oeros-scarthgap-jazzy-raspberrypi5.yml`, with `smrbx-shared.yml` on top.

On the build host (the commit is the one these builds used):

```bash
git clone -b build https://github.com/ros/meta-ros.git meta-ros-build
git -C meta-ros-build checkout 4212d293d5779d3c3b8c445de15066e640d2e601
cp yocto/kas/*.yml         meta-ros-build/kas/
cp yocto/kas/machine/*.yml meta-ros-build/kas/machine/
# meta-smrbx is referenced by absolute path from smrbx-shared.yml:
cp -r yocto/meta-smrbx <work dir>/buildx-yocto/meta-smrbx
```

`smrbx-shared.yml` points at `/work/buildx-yocto/meta-smrbx`, `/work/downloads` and
`/work/sstate`, because the builds run kas inside a container with the work
directory mounted at `/work`. Adjust those paths if you run kas differently.

Build commands (KV260; swap `kv` for `kr` for the KR260):

```bash
CFG=kas/oeros-scarthgap-jazzy-k26-smk-kv-sdt.yml:kas/smrbx-shared.yml
kas build $CFG                                                          # board image (ros-image-core)
kas shell $CFG -c 'bitbake ros2-image-sdktest -c populate_sdk'          # SDK for dockerfiles/oesdk / --method sdk
kas shell $CFG -c 'bitbake ros-dev-container'                           # OCI dev container

# Raspberry Pi 5: the same three commands with
CFG=kas/oeros-scarthgap-jazzy-raspberrypi5.yml:kas/smrbx-shared.yml
```

Bitbake must not run as root. The host in use had no pip and no sudo, so kas ran
inside an `ubuntu:24.04` container with the Yocto host packages, as a uid-1000 user
matching the host.

## Why the machine files look the way they do

Each of these cost a failed build. They are commented inline too; don't "tidy" them
away.

- **`k26-smk-kv-sdt` / `k26-smk-kr-sdt`, not `k26-smk-kv` / `k26-smk-kr`.** The plain
  machines set `XILINX_WITH_ESW = "xsct"`, and XSCT is an x86_64-only AMD binary. The
  SDT (system device tree) variants download prebuilt SDT artifacts and process them
  with lopper, which runs on any host.
- **meta-xilinx on `rel-v2025.2`, not `scarthgap`.** meta-kria `rel-v2025.2` inherits
  `amd_spi_image.bbclass`, which exists only on meta-xilinx's `rel-v*` branches. That
  branch still declares `LAYERSERIES_COMPAT = "scarthgap"`. Both land on tag
  `amd-edf-rel-v25.11.1`, and all four Xilinx-side repos are pinned to exact commits.
- **`meta-xilinx-multimedia` is included.** The machines set
  `MACHINE_HWCODECS = "libvcu-omxil"` and add the `hwcodecs` image feature, so the image
  fails with `Nothing RPROVIDES 'libvcu-omxil'` without that layer.
- **`FSBL_DEPLOY_DIR:forcevariable` / `PMU_FIRMWARE_DEPLOY_DIR:forcevariable`.** meta-ros's
  `ros2` distro builds into `tmp-glibc`, while the firmware multiconfigs
  (`DISTRO = "xilinx-standalone"`) build into `tmp-<mc>`. The machine conf derives the
  firmware location from the consumer's TMPDIR, so it looks in `tmp-glibc-<mc>` and
  FSBL/PMU fail at the very end of the build. `:forcevariable` is required, because
  `machine.conf` is parsed after `local.conf` and assigns these with a plain `=`.

## What `smrbx-shared.yml` adds

- Shared `DL_DIR` / `SSTATE_DIR` across machines, and `wic.bz2` + `wic.bmap` outputs.
- **`TOOLCHAIN_HOST_TASK:append = " nativesdk-ros-sdk-env"`.** `ros-sdk-env` is what sets
  `OE_CMAKE_TOOLCHAIN_FILE`, `PYTHON_SOABI` and `AMENT_PREFIX_PATH` in the SDK, and
  nothing in meta-ros references it: not `ROS_SDK_HOST_PACKAGES`, not any image. Without
  this line the SDK can't configure a ROS workspace. Build the SDK from
  `ros2-image-sdktest`; `ros-image-core -c populate_sdk` also lacks colcon.
- **`ssh-server-openssh` + `rsync`** in the images, so workspaces can be deployed over
  SSH. OpenSSH rather than dropbear: modern `scp` uses SFTP, which dropbear lacks.
- **`SDKIMAGE_FEATURES = "dev-pkgs"`.** The SDK is for building against, not for
  debugging on. With the default `dev-pkgs dbg-pkgs src-pkgs`, debug symbols made up 72 %
  of the KV260 SDK's target sysroot and debug sources another 8 %. Dropping them shrank
  the installer from 1.1 GB to 272 MB.

## meta-smrbx

- **`recipes-connectivity/openssh/openssh_%.bbappend`** appends `IPQoS none` to
  `sshd_config`. On the KV260, interactive SSH died after ~18 s with "Broken pipe"
  while commands without a terminal worked. With a PTY, OpenSSH switches its packets to
  an interactive DSCP marking, and the board's marked replies were lost on the way to
  the LAN. Server-side `IPQoS none` fixes it; client-side does not.
- **`recipes-core/images/ros-dev-container.bb`** — see below.

## The dev container (`ros-dev-container`)

An aarch64 OCI image of the meta-ros userspace with compilers and `-dev` packages,
built from **the same configuration as the board image**. colcon-buildx uses it
through its normal Docker path for images that run as the target architecture, so a
workspace is compiled natively against exactly the libraries the board ships. There
is no Ubuntu base and no cross toolchain.

The published ones are pulled like any image:

```bash
colcon buildx --method docker --docker-platform linux/arm64 \
  --docker-image ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy   # or rpi5-yocto-jazzy
```

Loading one you built yourself needs `skopeo`. Bitbake's OCI archive records only the
tag (`jazzy`) as its reference name and no platform, so a plain `docker load` leaves an
image Docker cannot resolve by name. `skopeo` converts it into a Docker archive with an
explicit name:

```bash
D=<build dir>/tmp-glibc/deploy/images/k26-smk-kv-sdt
docker run --rm --user $(id -u):$(id -g) -v "$D:/in:ro" -v /tmp:/out quay.io/skopeo/stable \
  copy oci-archive:/in/ros-dev-container-jazzy-jazzy-oci.tar:jazzy \
       docker-archive:/out/devctr.tar:ros-dev-container:jazzy
docker load -i /tmp/devctr.tar

colcon buildx --method docker --docker-image ros-dev-container:jazzy --docker-platform linux/arm64
```

It carries the label `org.smarobix.buildx.kind=yocto-native`, together with
`ros-distro` and `target-platform`. It's 1.38 GB unpacked and a 215 MB download (232 MB
for the Pi 5). Verified on 2026-09-13 on an arm64
host: an interface package plus an `rclcpp` node that depends on it build in 16 s cold
and 9 s incremental, with colcon-buildx running as a normal user. The result **runs on
the KV260**: `talker` at 2 Hz, 26.5 MB RSS. Unlike the SDK builds, `ros2 topic echo`
also decodes the custom message there, because this container generates Python
bindings as well.

The Raspberry Pi 5 container (1.41 GB) builds the same workspace in 16 s cold and 9 s
incremental. The result is an aarch64 binary that needs no `libatomic`. It has not been
run on a Pi 5 board yet.

It runs natively on arm64 hosts, including Apple Silicon. On x86_64 it should run under
QEMU, only slower, but that hasn't been tried yet. The SDK image, by contrast, would need
a second SDK built for x86_64 hosts.

Recipe choices in `ros-dev-container.bb`, each prompted by a failure:

- `IMAGE_FSTYPES:remove = "wic.bz2 wic.bmap"`: `smrbx-shared.yml` appends those for the
  board images, and an `:append` lands after the recipe's own `IMAGE_FSTYPES = "oci"`,
  so without this bitbake also writes a useless disk image of the container's rootfs.
- `inherit image-container image-oci`: the `oci` image type depends on OE-core's
  `container` type. `IMAGE_CONTAINER_NO_DUMMY = "1"` opts out of `image-container`'s
  demand for a `linux-dummy` kernel; the container installs no kernel, and the board
  image built from the same configuration needs the real one.
- `OCI_IMAGE_ENTRYPOINT = ""`: the default entrypoint `sh` would turn colcon-buildx's
  `bash -c '…'` into `sh bash -c …`.
- No `packagegroup-core-boot` (no init system in a container), which also means no
  busybox, so `sed grep gawk tar gzip which` are listed explicitly.
- `xz`: `dockerfiles/oesdk` builds the SDK image on top of this container, and the SDK
  installer's payload is xz-compressed.
- `python-cmake-module`: `rosidl_generator_py` `find_package()`s it, and every interface
  package fails to configure without it. Unlike the SDK, this container has the Python
  message generator, so interface packages get Python bindings too.
- `OCI_IMAGE_ENV_VARS = "LDFLAGS=-Wl,-O1,--hash-style=gnu,--as-needed"`: link the way the
  distro does. `rcutils` exports `-latomic` to every package that uses it. OE builds and
  the SDK link with `--as-needed`, so the unused library is dropped. Without these flags
  the container kept it as a hard dependency, and the binary failed on the board
  (`libatomic.so.1: cannot open shared object file`), because the board doesn't ship
  libatomic. It's written as one token because `OCI_IMAGE_ENV_VARS` is space-separated.
- `IMAGE_FEATURES += "tools-sdk dev-pkgs"`: target compilers, plus the headers and CMake
  configs of everything installed.

## The board image

`ros-image-core`: `ros-core` only (includes `rclcpp`), no demo nodes. On the board:

- Log in as `root` with an empty password (serial console or SSH). Bench use only.
- There is **no bash**, only BusyBox ash: source `/opt/ros/jazzy/setup.sh`, not
  `setup.bash`. BusyBox here has no `timeout` and only `head -n N`.
- The NIC is `end0`; DHCP via systemd-networkd / connman.
- Flash the image that matches the carrier (U-Boot prints `SCK-KV-G` or `SCK-KR-G` at
  boot). Boot from SD; don't write `boot.bin` to QSPI unless the card won't boot.
