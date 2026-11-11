---
hide:
  - toc
---

# SMAROBIX buildx

Build your ROS 2 workspace on your own computer for the robot or board it runs on, and put ROS 2 on 32-bit ARM boards that have no official ROS 2 packages.

[OEROS](https://github.com/oerosproject) is a reference distribution for ROS 2 robots, built with Yocto and meta-ros. Besides the robot's image, it publishes a stack of container images, among them SDK images that build software for the robot. colcon buildx uses those to build your workspace for a robot that runs OEROS.

Two repositories make one toolchain:

- **smarobix-colcon-buildx** is the `colcon buildx` verb. It builds your workspace against the robot's or the board's image, on your computer's own architecture, and copies the result to the board. Nothing runs under emulation.
- **smarobix-buildx-images** publishes images of 32-bit ARM boards, and ROS 2 for those boards as `.deb` packages.

## Two jobs

Getting your code onto a board takes two jobs, and these pages keep them apart.

1. **Put ROS 2 on the board.** On an OEROS robot it is part of the image. On a 32-bit board, install the `.deb` from this project.
2. **Build your workspace** with `colcon buildx` on your computer, against the robot's image. This part is the same on every board.

## Which boards

| Board | Its operating system | ROS 2 on the board | `docker_image` for colcon buildx |
|---|---|---|---|
| A robot running OEROS | OEROS, arm64 | part of the image | `oeros-sdk-cross` or `oeros-sdk-target`, see [OEROS robots](tool/oeros.md) |
| Pynq-Z1, Pynq-Z2 | PYNQ v3.1.1: Ubuntu 22.04, 32-bit | `.deb` from this project | `pynq-v3.1.1-jazzy` |
| Raspberry Pi 2 and newer, Zero 2 W | Raspberry Pi OS or Debian, 32-bit | `.deb` from this project | `rpi-armv7-trixie-jazzy` |
| Kria K26 | this project's Yocto image | part of the image | `k26-oesdk-jazzy`, see [Yocto boards](guides/yocto.md) |

**64-bit boards on Ubuntu or Debian** are not covered here, a Kria K26 with Ubuntu or a Raspberry Pi with 64-bit Raspberry Pi OS among them. [pixi and RoboStack](https://robostack.github.io/) put every current ROS 2 distro on them and cross-build for them from an x86 computer. [How it works](how-it-works.md) explains the split.

The [targets reference](reference/targets.md) lists every published image. These pages use ROS 2 Jazzy for the 32-bit boards, where Humble works the same way, and Lyrical for OEROS, which publishes Lyrical.

## Start here

[Set up your computer](start/setup.md), then follow the four steps in order. Pick your board in the tabs once; the choice follows you through the site.
