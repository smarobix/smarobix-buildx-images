# How it works

## Why these boards need help

ROS 2 is distributed as binary apt packages for a few operating systems only. [REP-2000](https://www.ros.org/reps/rep-2000.html) assigns support tiers to architectures, but the buildfarm publishes per *(OS release, architecture)* pair, so a Tier 1 architecture on an OS the buildfarm does not target has no binaries at all. Ubuntu on arm64 has thousands of packages. Debian, and with it Raspberry Pi OS, has none on any architecture, and Ubuntu on armhf has none either; those dists carry only bootstrap tooling such as `ros-dev-tools`. Count it for your own board rather than assuming:

```bash
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/<codename>/main/binary-<arch>/Packages.gz \
  | gunzip | grep -c '^Package: ros-<distro>-'
```

## Who covers what

**64-bit boards on Ubuntu or Debian** are covered well without this project. [RoboStack](https://robostack.github.io/) publishes every current ROS 2 distro as conda packages for linux-aarch64, and [pixi](https://pixi.sh) installs them beside whatever the board runs, on any arm64 Linux with glibc 2.17 or newer, Kria K26 on Ubuntu and Raspberry Pi OS 64-bit included. pixi also cross-builds packages for those boards from an x86 computer. We measured both on a Kria K26 and an Ultra96 before narrowing this project down.

**32-bit boards** are where that stops: conda-forge has no current packages for 32-bit ARM, and the buildfarm has none either. Without binaries such a board has two bad options: build ROS 2 on the board, which takes hours on a small machine and has to be repeated when the OS moves a library, or build it as part of every workspace. This project builds it once per target in CI, scopes it to a useful subset of `ros-base`, and ships the install tree as a `.deb` that drops into `/opt/ros/<distro>` with real dependencies on the board's own libraries. That is the Pynq and 32-bit Raspberry Pi OS case.

**Yocto robots** need neither: bitbake builds ROS 2 into the robot's image. [OEROS](https://github.com/oerosproject) publishes such images, and SDK images that build for them; colcon buildx builds your workspace with those.

## Two worlds

Every target belongs to one of two worlds, and they do not mix. In the Ubuntu and Debian world, ROS 2 is installed on top of a general-purpose distribution and links against its libc, Python and OpenCV; the board images mirror that, with the same base and the same packages. In the Yocto world the image is built from recipes, with nothing on it that was not asked for. Binaries built for one world do not run on the other, and a workspace that has to run on both needs one build per world.

## Nothing runs under emulation

colcon buildx builds on your computer's own architecture, always. What it does with an image depends on the image's labels and architecture:

- **An SDK image**, such as the OEROS ones, holds a cross toolchain and the robot's sysroot and runs on your computer. colcon buildx adds a thin layer with what the SDK lacks, once per image version, and builds through a toolchain wrapper. [OEROS robots](tool/oeros.md#how-colcon-buildx-works-with-an-oeros-image) draws it.
- **A board image of another architecture**, such as `pynq-v3.1.1-jazzy` on an x86_64 or arm64 computer, becomes the sysroot of a *cross image*: its filesystem is copied, without running anything from it, into an image of your computer's architecture with the same Ubuntu or Debian release's cross compiler. Compiler, glibc and Python then match the board by construction, and Python modules get the board's file names.
- **An image of your computer's architecture** runs as it is.

QEMU still has one job, outside colcon buildx: building the board images in CI, where their `apt-get install` steps run as the board.

Nothing stops you using an image without colcon buildx, with `docker run` and `colcon build` inside. What you give up is the cross image, the SDK preparation and the toolchain wrapper, and a build owned by your user and kept apart from a host build.

## One middleware: Cyclone DDS

ROS 2 picks its DDS middleware at run time from `RMW_IMPLEMENTATION`. Both Fast DDS and Cyclone DDS are in every install tree here, nothing sets the variable, and unset means Fast DDS. The recommendation is Cyclone DDS on every board, for two reasons. Its memory footprint is markedly smaller, which matters on a 512 MB Pynq and on a 32-bit Pi. And one answer everywhere means no two machines in a fleet that cannot hear each other because they chose differently. Export it in every shell that runs a node, on every machine, your laptop included; for a systemd unit, `Environment=RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`.

## What is in a `.deb`

The tree is `ros-base` minus the display packages: `rclcpp`, `rclpy`, the `ros2` command line, `launch`, the common interface packages, `tf2`, `urdf`, `robot_state_publisher`, `rosbag2`, `sros2`, both RMW implementations, `cv_bridge` and `image_transport`, plus `demo_nodes_cpp` and the minimal examples for checking a board. `rviz2` and `rqt` are left out; these boards run headless. A package missing from the tree goes into your workspace as source.

The package name is `smarobix-ros-<distro>-<pkg>`, where `<pkg>` names the release the tree was built against (`rpi-trixie`, `rpi-bookworm`, `pynq-v3.1.1`), because the release decides whether the tree runs: trixie and bookworm differ in `libpython`, `libstdc++` and OpenCV. The file name adds the version and the dpkg architecture. `Depends` is computed from what the built binaries link against, so it cannot drift; `Recommends` carries optional features such as `python3-opencv`; `Suggests` is the toolchain for compiling on the board itself, which apt does not install. Upgrade by installing a newer file, remove with `apt remove`.

Two limits. The 32-bit packages are ARMv7, so they run on a Pi 2 and newer and on any ARMv7 Debian board, but not on the ARMv6 Pi 1, Zero and Zero W. And on a Pynq board, `cv_bridge` links an OpenCV that was built into the image under `/opt/install`, which the package neither ships nor declares; check with `ldd /opt/ros/jazzy/lib/libcv_bridge.so | grep 'not found'` before relying on it.

Image tags roll: a tag is rebuilt on every push to `main`, and there are no versioned tags. Pin the digest, which `docker buildx imagetools inspect` prints, when a build has to be reproducible, and take the image and the `.deb` from the same release when it matters.
