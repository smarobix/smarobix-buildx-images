# Pick a target

A target is one combination of board, operating system, architecture and ROS 2 distro.
It decides two things: how ROS 2 gets onto the board, and which image `colcon buildx`
builds your workspace in. Both answers have to match the board exactly, because a ROS 2
install tree only runs against the libraries it was linked with.

The [target picker](https://smarobix.github.io/smarobix-buildx-images/) asks these
questions and prints the commands. The rules below are the same decision written out.

## 1. Ask the board what it runs

On a Debian or Ubuntu userspace:

```bash
. /etc/os-release && echo "$NAME $VERSION_ID $VERSION_CODENAME"
dpkg --print-architecture     # arm64 or armhf
uname -m                      # aarch64 or armv7l
```

A board running a Yocto image has no `dpkg`, and its `/etc/os-release` and `/etc/issue`
name the meta-ros distro rather than Debian or Ubuntu.

Check the running system, not the image you think you wrote to the card. A `.deb` or an
image built for the wrong release installs cleanly and then fails at the first `ros2`
call.

## 2. Follow the rule for that OS

**Kria K26 (KV260, KR260) on Ubuntu.** ROS 2 comes from packages.ros.org, nothing from
here: Ubuntu 22.04 carries Humble, Ubuntu 24.04 carries Jazzy. The build image is
`k26-humble` or `k26-jazzy`, platform `linux/arm64`. Start with
[Cross-build your first workspace](../tutorials/first-cross-build.md).

**Pynq-Z1 or Pynq-Z2 on the PYNQ image.** The build image is `pynq-v3.1.1-jazzy` or
`pynq-v3.1.1-humble`, platform `linux/arm/v7`, and ROS 2 goes on the board as
`smarobix-ros-<distro>-pynq-v3.1.1_1.1.0_armhf.deb`. The version in the name is the
PYNQ release the image is built against; check which PYNQ image your card was written
from on the [PYNQ releases page](https://github.com/Xilinx/PYNQ/releases). Both boards
use the same Zynq-7020 SoC and the same artifacts.

**Raspberry Pi OS or Debian, bookworm or trixie.** ROS 2 goes on the board as a `.deb`
from the release. Take the architecture from `dpkg --print-architecture` and the
release from `VERSION_CODENAME`:

| Board runs | Build image | `.deb` |
|---|---|---|
| 64-bit, trixie | `rpi-arm64-trixie-<distro>` | `smarobix-ros-<distro>-rpi-trixie_1.1.0_arm64.deb` |
| 64-bit, bookworm | `rpi-arm64-bookworm-<distro>` | `smarobix-ros-<distro>-rpi-bookworm_1.1.0_arm64.deb` |
| 32-bit, trixie | `rpi-armv7-trixie-<distro>` | `smarobix-ros-<distro>-rpi-trixie_1.1.0_armhf.deb` |
| 32-bit, bookworm | `rpi-armv7-bookworm-<distro>` | `smarobix-ros-<distro>-rpi-bookworm_1.1.0_armhf.deb` |

`<distro>` is `jazzy` or `humble`. Nothing in these images is Raspberry-Pi-specific:
the base is stock Debian, so they suit any Debian board of the same release and
architecture. The 32-bit builds are ARMv7, which excludes the ARMv6 Pi 1, Zero and
Zero W.

**A Yocto / meta-ros board (K26 or Raspberry Pi 5).** ROS 2 is already in the board
image, built from [`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto);
board images are not published. For building your workspace there are two images per
board, both Jazzy: the dev container (`k26-yocto-jazzy`, `rpi5-yocto-jazzy`), which
compiles natively as the board and also generates Python message bindings, and the SDK
image (`k26-oesdk-jazzy`, `rpi5-oesdk-jazzy`), which cross-compiles on the host and
does not. [Native or cross](../explanation/native-vs-cross.md) compares them, and
[colcon-buildx on meta-ros](../tutorials/meta-ros.md) walks through both.

## 3. Choosing the ROS 2 distro, when you have a choice

On Ubuntu the OS release decides. On Debian and PYNQ both Humble and Jazzy are
published, so pick the one the rest of your fleet runs. Upstream support ends in May
2027 for Humble and May 2029 for Jazzy.

## What cannot be mixed

- A `.deb` or image built for one Debian release does not work on another: bookworm and
  trixie ship different `libpython`, `libstdc++` and OpenCV versions.
- Ubuntu-based and Yocto-based artifacts do not mix in either direction. See
  [Ubuntu or Yocto](../explanation/ubuntu-vs-yocto.md).
- The architecture of the image and of the board's userspace must agree. A 64-bit board
  running a 32-bit OS needs the `armhf` artifacts.

## Then

- The full list, with platform, `.deb` name and what has been run on hardware:
  [Targets](../reference/targets.md).
- Whether anyone has run that target on a board: [Tested hardware](../reference/tested-hardware.md).
- A board that is not listed: [Add a board](../maintain/add-a-board.md).
