<!-- Generated from targets.yml by tools/targets.py docs. Do not edit. -->

# Targets

Generated from [`targets.yml`](https://github.com/smarobix/smarobix-buildx-images/blob/main/targets.yml); do not edit this page by hand.

Every image is published as `ghcr.io/smarobix/smarobix-buildx-images:<tag>`, with the tag from the first column, for example `ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy`.

The `.deb` column names the Debian package that every `v*` release attaches for that target, as `<package>_<version>_<arch>.deb` next to a `.tar.gz` of the same tree. `<version>` is the release tag without the `v`, and `<arch>` is the Arch column; [.deb packages](deb-packages.md) describes them.

RMW is the recommendation the `.deb` prints when it installs. Nothing sets `RMW_IMPLEMENTATION`, so you export it yourself; [Which RMW](../explanation/rmw.md) says why. Tested lists dated runs on real hardware, with the details under the table and in [Tested hardware](tested-hardware.md).

## Ubuntu with the official ROS 2 packages (`ubuntu-apt`)

ROS 2 on the board comes from the official apt packages at packages.ros.org. These images are for cross-building your workspace; no `.deb` is published.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | RMW | Tested |
|---|---|---|---|---|---|---|---|
| `k26-jazzy` | Kria K26 (KV260 / KR260) | Ubuntu 24.04 (`noble`) | `arm64` | `linux/arm64` | none | `rmw_cyclonedds_cpp` | not yet |
| `k26-humble` | Kria K26 (KV260 / KR260) | Ubuntu 22.04 (`jammy`) | `arm64` | `linux/arm64` | none | `rmw_cyclonedds_cpp` | not yet |

## PYNQ (`pynq`)

ROS 2 is built from source against the PYNQ SD-card image the tag names, and published as a `.deb` for the board.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | RMW | Tested |
|---|---|---|---|---|---|---|---|
| `pynq-v3.1.1-jazzy` | Xilinx Zynq-7020 boards (Pynq-Z1 / Pynq-Z2) | PYNQ v3.1.1, Ubuntu 22.04 (`jammy`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-pynq-v3.1.1` | `rmw_cyclonedds_cpp` | not yet |
| `pynq-v3.1.1-humble` | Xilinx Zynq-7020 boards (Pynq-Z1 / Pynq-Z2) | PYNQ v3.1.1, Ubuntu 22.04 (`jammy`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-pynq-v3.1.1` | `rmw_cyclonedds_cpp` | not yet |

## Raspberry Pi OS and Debian (`debian`)

Debian has no official ROS 2 binaries, so ROS 2 is built from source on stock Debian, per suite and architecture, and published as a `.deb`. Nothing in these images is specific to the Raspberry Pi.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | RMW | Tested |
|---|---|---|---|---|---|---|---|
| `rpi-arm64-trixie-jazzy` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `arm64` | `linux/arm64` | `smarobix-ros-jazzy-rpi-trixie` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-arm64-trixie-humble` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `arm64` | `linux/arm64` | `smarobix-ros-humble-rpi-trixie` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-armv7-trixie-jazzy` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-rpi-trixie` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-armv7-trixie-humble` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 13 / Debian 13 (`trixie`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-rpi-trixie` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-arm64-bookworm-jazzy` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `arm64` | `linux/arm64` | `smarobix-ros-jazzy-rpi-bookworm` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-arm64-bookworm-humble` | any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `arm64` | `linux/arm64` | `smarobix-ros-humble-rpi-bookworm` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-armv7-bookworm-jazzy` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `armhf` | `linux/arm/v7` | `smarobix-ros-jazzy-rpi-bookworm` | `rmw_cyclonedds_cpp` | not yet |
| `rpi-armv7-bookworm-humble` | any ARMv7 Raspberry Pi (2, 3, 4, 5, Zero 2 W) on a 32-bit OS; not Pi 1 / Zero / Zero W | Raspberry Pi OS 12 / Debian 12 (`bookworm`) | `armhf` | `linux/arm/v7` | `smarobix-ros-humble-rpi-bookworm` | `rmw_cyclonedds_cpp` | not yet |

## Yocto dev containers (`yocto-native`)

The board's own meta-ros userspace plus compilers, built by bitbake from the same configuration as the board image and pushed by hand. They run as the target. ROS 2 on the board is part of the Yocto board image, which is not published.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | RMW | Tested |
|---|---|---|---|---|---|---|---|
| `k26-yocto-jazzy` | Kria K26 (KV260 / KR260) running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | `linux/arm64` | none | `rmw_cyclonedds_cpp` | 2026-09-13, KV260 |
| `rpi5-yocto-jazzy` | Raspberry Pi 5 running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | `linux/arm64` | none | `rmw_cyclonedds_cpp` | not yet |

- `k26-yocto-jazzy` on the KV260, 2026-09-13: An interface package and an rclcpp node that depends on it, built in this container, ran on the KV260 (talker at 2 Hz, 26.5 MB RSS).

## Yocto SDK cross images (`oe-sdk`)

The meta-ros SDK installed on top of the matching dev container. The image carries a cross toolchain and runs on the host rather than as the target, so it has no target platform and is started without `--platform`. The tag has only a `linux/arm64` image; on an x86_64 host, pull it with `--platform linux/arm64` first.

| Tag | Boards | OS | Arch | Docker platform | `.deb` package | RMW | Tested |
|---|---|---|---|---|---|---|---|
| `k26-oesdk-jazzy` | Kria K26 (KV260 / KR260) running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | none (runs on the host) | none | `rmw_cyclonedds_cpp` | 2026-09-15, KV260 |
| `rpi5-oesdk-jazzy` | Raspberry Pi 5 running the Yocto image built from yocto/ | Yocto / meta-ros (`scarthgap`) | `arm64` | none (runs on the host) | none | `rmw_cyclonedds_cpp` | not yet |

- `k26-oesdk-jazzy` on the KV260, 2026-09-15: Binaries built with the same SDK, installed on an Ubuntu base rather than on the dev container, ran unmodified on a KV260 booted from the matching Yocto image.
