<!-- Generated from targets.yml by tools/targets.py docs. Do not edit. -->

# Targets

Every published image, generated from [`targets.yml`](https://github.com/smarobix/smarobix-buildx-images/blob/main/targets.yml). An image is `ghcr.io/smarobix/smarobix-buildx-images:<tag>`, for example `ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy`.

Where a `.deb` package is named, every `v*` [release](https://github.com/smarobix/smarobix-buildx-images/releases) attaches it as `<package>_<version>_<arch>.deb`, next to a `.tar.gz` of the same tree; [How it works](../how-it-works.md#what-is-in-a-deb) describes the packages. Tested lists dated runs on real hardware; "not yet" means built, but not run on a board.

## Ubuntu with the official ROS 2 packages (`ubuntu-apt`)

ROS 2 on the board comes from the official apt packages at packages.ros.org. These images are for cross-building your workspace; no `.deb` is published.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |
|---|---|---|---|---|---|---|
| `k26-jazzy` | Kria K26 (KV260 / KR260) | Ubuntu 24.04 (`noble`) | `arm64` | `linux/arm64` | none | not yet |
| `k26-humble` | Kria K26 (KV260 / KR260) | Ubuntu 22.04 (`jammy`) | `arm64` | `linux/arm64` | none | not yet |

## PYNQ (`pynq`)

ROS 2 is built from source against the PYNQ SD-card image the tag names, and published as a `.deb` for the board.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |
|---|---|---|---|---|---|---|
| `pynq-v3.1.1-jazzy` | Xilinx Zynq-7020 boards (Pynq-Z1 / Pynq-Z2) | PYNQ v3.1.1, Ubuntu 22.04 (`jammy`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-pynq-v3.1.1` | not yet |
| `pynq-v3.1.1-humble` | Xilinx Zynq-7020 boards (Pynq-Z1 / Pynq-Z2) | PYNQ v3.1.1, Ubuntu 22.04 (`jammy`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-pynq-v3.1.1` | not yet |

## Raspberry Pi OS and Debian (`debian`)

Debian has no official ROS 2 binaries, so ROS 2 is built from source on stock Debian, per suite and architecture, and published as a `.deb`. Nothing in these images is specific to the Raspberry Pi.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |
|---|---|---|---|---|---|---|
| `rpi-arm64-trixie-jazzy` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `arm64` | `linux/arm64` | `smarobix-ros-jazzy-rpi-trixie` | not yet |
| `rpi-arm64-trixie-humble` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `arm64` | `linux/arm64` | `smarobix-ros-humble-rpi-trixie` | not yet |
| `rpi-armv7-trixie-jazzy` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-rpi-trixie` | not yet |
| `rpi-armv7-trixie-humble` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-rpi-trixie` | not yet |
| `rpi-arm64-bookworm-jazzy` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `arm64` | `linux/arm64` | `smarobix-ros-jazzy-rpi-bookworm` | not yet |
| `rpi-arm64-bookworm-humble` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `arm64` | `linux/arm64` | `smarobix-ros-humble-rpi-bookworm` | not yet |
| `rpi-armv7-bookworm-jazzy` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-rpi-bookworm` | not yet |
| `rpi-armv7-bookworm-humble` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-rpi-bookworm` | not yet |

## Yocto dev containers (`yocto-native`)

The board's own meta-ros userspace plus compilers, built by bitbake from the same configuration as the board image and pushed by hand. They run as the target. ROS 2 on the board is part of the Yocto board image, which is not published.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |
|---|---|---|---|---|---|---|
| `k26-yocto-jazzy` | Kria K26 (KV260 / KR260) running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | `linux/arm64` | none | 2026-09-13, KV260 |
| `rpi5-yocto-jazzy` | Raspberry Pi 5 running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | `linux/arm64` | none | not yet |

## Yocto SDK cross images (`oe-sdk`)

The meta-ros SDK installed on top of the matching dev container. The image carries a cross toolchain and runs on the host rather than as the target, so it has no target platform and is started without `--platform`. The tag has only a `linux/arm64` image; on an x86_64 host, pull it with `--platform linux/arm64` first.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |
|---|---|---|---|---|---|---|
| `k26-oesdk-jazzy` | Kria K26 (KV260 / KR260) running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | none (runs on the host) | none | 2026-09-15, KV260 |
| `rpi5-oesdk-jazzy` | Raspberry Pi 5 running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | none (runs on the host) | none | not yet |
