# Yocto boards

A Kria K26 or a Raspberry Pi 5 can run an image that bitbake builds from [meta-ros](https://github.com/ros/meta-ros): kernel, userspace and ROS 2 in one, pinned by recipe. This project's [`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto) directory holds the configuration. It is a different world from Ubuntu: there is no apt, binaries built against Ubuntu or Debian do not run there, and binaries built here do not run on Ubuntu.

What a first-time user hits: the image logs in as `root` with an empty password, it has no bash (source `setup.sh`, not `setup.bash`), and adding software means rebuilding the image.

## Build and flash the board image

Board images are not published. The kas files in `yocto/` overlay meta-ros's own `build`-branch configs, pinned to the commit these builds used, and add the Kria machines and a small layer. The builds ran on an arm64 Linux host; bitbake must not run as root.

```bash
git clone -b build https://github.com/ros/meta-ros.git meta-ros-build
git -C meta-ros-build checkout 4212d293d5779d3c3b8c445de15066e640d2e601
cp yocto/kas/*.yml         meta-ros-build/kas/
cp yocto/kas/machine/*.yml meta-ros-build/kas/machine/
cp -r yocto/meta-smrbx     /work/buildx-yocto/meta-smrbx    # the path smrbx-shared.yml names
cd meta-ros-build
CFG=kas/oeros-scarthgap-jazzy-k26-smk-kv-sdt.yml:kas/smrbx-shared.yml   # kv: KV260; kr: KR260
kas build $CFG
```

For a Raspberry Pi 5, `CFG=kas/oeros-scarthgap-jazzy-raspberrypi5.yml:kas/smrbx-shared.yml`. `smrbx-shared.yml` puts the download and sstate caches under `/work` and sets 12 build threads; adjust both to your machine. Every unusual setting in the kas files has a comment beside it saying which failure it prevents.

The image lands in `build/tmp-glibc/deploy/images/<machine>/ros-image-core-jazzy-<machine>.rootfs.wic.bz2`, with a `.wic.bmap` beside it. Write it to an SD card with `bmaptool copy` and boot from the card. On a Kria, U-Boot prints `SCK-KV-G` or `SCK-KR-G` at boot: flash the image for that carrier, and leave the QSPI firmware alone unless the card will not boot.

## Three ways to build a workspace

All three link against the meta-ros sysroot and produce binaries for the board image. The tutorial uses the first.

| Route | Kria K26 | Raspberry Pi 5 | Runs on | Python message bindings |
|---|---|---|---|---|
| Dev container | `k26-yocto-jazzy` | `rpi5-yocto-jazzy` | any host with Docker, as the board; QEMU on x86_64 | yes |
| SDK image | `k26-oesdk-jazzy` | `rpi5-oesdk-jazzy` | any host with Docker, cross-compiling on the host | no |
| SDK installed on the host | `environment-setup-cortexa72-cortexa53-oe-linux` | `environment-setup-cortexa76-oe-linux` | arm64 Linux only | no |

**Dev container.** An image of the board's own userspace plus compilers, built by bitbake from the same configuration as the board image. This is the `.buildx.conf` in the tutorial.

**SDK image.** The meta-ros SDK installed on top of the dev container. It carries a cross toolchain and runs on the host's architecture, so colcon-buildx starts it without `--platform`, sources the SDK environment and builds with Ninja, all of which it reads from the image's [labels](../tool/labels.md). In `.buildx.conf`, name the tag and drop `docker_platform`. The published tags have only an arm64 entry, so on an x86_64 host pull once with the platform first, or the build fails with "no matching manifest":

```bash
docker pull --platform linux/arm64 ghcr.io/smarobix/smarobix-buildx-images:k26-oesdk-jazzy
```

**SDK on the host.** The way meta-ros intends its SDKs to be used. Download the installer for your board from the [SDK releases](https://github.com/smarobix/smarobix-buildx-images/releases?q=yocto-sdk), whose notes list each file's sha256, then:

```bash
sh oecore-*.sh -y -d /opt/ros-sdk
colcon buildx --method sdk --sdk-env /opt/ros-sdk/environment-setup-cortexa72-cortexa53-oe-linux \
  --cmake-args -DBUILD_TESTING=OFF
```

Both SDK routes need an SDK built with `ros-sdk-env`, which sets the toolchain file, `PYTHON_SOABI` and `AMENT_PREFIX_PATH`. The published ones have it, and colcon-buildx stops with a clear error when one does not. Neither route generates Python message bindings, because meta-ros SDKs ship no `rosidl_generator_py`: on the board, `ros2 topic echo` then sees a custom message type but cannot decode it. Build interface packages in the dev container if you need them.

Around the SDK's toolchain file, colcon-buildx writes a wrapper in `cross_build/` that lets a package find the ones built before it in the same workspace, and `--emit-mixin` writes the same settings as a colcon mixin for a plain `colcon build`.

## On the board

`--deploy` works: the images built from `yocto/` include OpenSSH and `rsync`. Sourcing needs the `.sh` scripts and, because a POSIX shell cannot tell where a sourced script lives, the workspace prefix by hand:

```sh
. /opt/ros/jazzy/setup.sh
COLCON_CURRENT_PREFIX=$HOME/ros2_ws/install . $HOME/ros2_ws/install/local_setup.sh
```

Rebuilding the SDKs and dev containers, and publishing them, is a maintainer job: [Rebuild the Yocto images](../maintain/yocto.md).
