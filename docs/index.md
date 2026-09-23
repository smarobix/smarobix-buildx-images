---
hide:
  - toc
---

# SMAROBIX buildx

Cross-build your ROS 2 workspace for an ARM board on your own computer, and put ROS 2 on boards that have no official ROS 2 packages.

Two repositories make one toolchain:

- **smarobix-buildx-images** publishes a Docker image for every supported board, OS and ROS 2 distro, and `.deb` packages of ROS 2 for the boards that have no binaries upstream.
- **smarobix-colcon-buildx** is the `colcon buildx` verb that builds your workspace inside one of those images and copies the result to the board.

## Two jobs

Getting your code onto a board takes two jobs. They are separate, and these pages keep them apart.

1. **Put ROS 2 on the board.** Where it comes from depends on the board: the official apt packages (Kria K26 on Ubuntu), a `.deb` from this project (Raspberry Pi, Debian, Pynq), or the board image itself (Yocto).
2. **Cross-build your workspace** with `colcon buildx` on your computer, in the image that matches the board. This part is the same on every board.

## Supported boards

| Board | ROS 2 on the board | Build images |
|---|---|---|
| Kria K26 (KV260, KR260) on Ubuntu | packages.ros.org | `k26-jazzy`, `k26-humble` |
| Raspberry Pi and other Debian boards, 64- and 32-bit | `.deb` from the releases | `rpi-arm64-*`, `rpi-armv7-*` |
| Pynq-Z1 and Pynq-Z2 on PYNQ v3.1.1 | `.deb` from the releases | `pynq-v3.1.1-jazzy`, `pynq-v3.1.1-humble` |
| Kria K26 and Raspberry Pi 5 on a Yocto / meta-ros image | built into the board image | `k26-yocto-jazzy`, `rpi5-yocto-jazzy`, and the SDK images |

The [targets reference](reference/targets.md) lists every tag with its platform and package. ROS 2 Jazzy and Humble are supported; the Yocto images are Jazzy only.

## Start here

[Set up your computer](start/setup.md), then follow the four steps in order. Pick your board in the tabs once; the choice follows you through the site.
