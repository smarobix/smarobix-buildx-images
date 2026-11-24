# Yocto boards

A Kria K26 can run an image that bitbake builds from [meta-ros](https://github.com/ros/meta-ros): kernel, userspace and ROS 2 in one, pinned by recipe. The Kria K26 is not an OEROS machine yet, so this project builds its image from meta-ros directly. This project's [`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto) directory holds the configuration. It is a different world from Ubuntu: there is no apt, binaries built against Ubuntu or Debian do not run there, and binaries built here do not run on Ubuntu.

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

`smrbx-shared.yml` puts the download and sstate caches under `/work` and sets 12 build threads; adjust both to your machine. Every unusual setting in the kas files has a comment beside it saying which failure it prevents.

The image lands in `build/tmp-glibc/deploy/images/<machine>/ros-image-core-jazzy-<machine>.rootfs.wic.bz2`, with a `.wic.bmap` beside it. Write it to an SD card with `bmaptool copy` and boot from the card. On a Kria, U-Boot prints `SCK-KV-G` or `SCK-KR-G` at boot: flash the image for that carrier, and leave the QSPI firmware alone unless the card will not boot.

## Build a workspace for it

Two images link against the board image's own sysroot. Both are built for arm64 computers, such as Apple silicon or an arm64 Linux machine:

| Route | Kria K26 | Python bindings for messages |
|---|---|---|
| SDK image | `k26-oesdk-jazzy` | no |
| Dev container | `k26-yocto-jazzy` | yes |

**SDK image.** The meta-ros SDK in a Docker image: a cross toolchain plus the board's sysroot. colcon buildx prepares it once and builds through its toolchain wrapper, exactly as for an [OEROS robot](../tool/oeros.md#how-colcon-buildx-works-with-an-oeros-image). Name the tag in `.buildx.conf`; nothing else is needed.

**Dev container.** The board's own userspace plus compilers, built by bitbake from the same configuration as the board image. It runs as the board, which on an arm64 computer needs no emulation, and it generates Python bindings for messages, which the SDK image cannot.

On an x86_64 computer, colcon buildx refuses both rather than emulate them. Building there needs an SDK made with `SDKMACHINE = "x86_64"`, which this project does not publish. For any other board, look at [OEROS](../tool/oeros.md) first: its SDK images come for x86_64 and arm64 computers alike.

## On the board

`--deploy` works: the images built from `yocto/` include OpenSSH and `rsync`. Sourcing needs the `.sh` scripts and, because a POSIX shell cannot tell where a sourced script lives, the workspace prefix by hand:

```sh
. /opt/ros/jazzy/setup.sh
COLCON_CURRENT_PREFIX=$HOME/ros2_ws/install . $HOME/ros2_ws/install/local_setup.sh
```

Rebuilding the SDKs and dev containers, and publishing them, is a maintainer job: [Rebuild the Yocto images](../maintain/yocto.md).
