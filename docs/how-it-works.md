# How it works

## Why these boards need help

ROS 2 is distributed as binary apt packages for a few operating systems only. [REP-2000](https://www.ros.org/reps/rep-2000.html) assigns support tiers to architectures, but the buildfarm publishes per *(OS release, architecture)* pair, so a Tier 1 architecture on an OS the buildfarm does not target has no binaries at all. Ubuntu on arm64 has thousands of packages. Debian, and with it Raspberry Pi OS, has none on any architecture, and Ubuntu on armhf has none either; those dists carry only bootstrap tooling such as `ros-dev-tools`. Count it for your own board rather than assuming:

```bash
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/<codename>/main/binary-<arch>/Packages.gz \
  | gunzip | grep -c '^Package: ros-<distro>-'
```

Without binaries a board has two bad options: build ROS 2 on the board, which takes hours on a small machine and has to be repeated when the OS moves a library, or build it as part of every workspace. This project builds it once per target in CI, scopes it to a useful subset of `ros-base`, and ships the install tree as a `.deb` that drops into `/opt/ros/<distro>` with real dependencies on the board's own libraries. That is the Raspberry Pi, Debian and Pynq case.

A Kria K26 on Ubuntu installs ROS 2 from packages.ros.org like any other Ubuntu machine. What it lacks is a *build* environment that matches the board: the same release and packages plus a cross toolchain, GStreamer and the Xilinx PPAs. That is what the `k26-*` images are. A Yocto board needs neither, because bitbake builds ROS 2 into the board image.

## Two worlds

Every target belongs to one of two worlds, and they do not mix. In the Ubuntu and Debian world, ROS 2 is installed on top of a general-purpose distribution and links against its libc, Python and OpenCV; the build images mirror that, with the same base and the same packages. In the Yocto world the image is built from recipes, with nothing on it that was not asked for. Binaries built for one world do not run on the other, and a workspace that has to run on both needs one build per world.

## Native and cross images

Most images run *as* the board: they hold its userspace, Docker runs them with `--platform linux/arm64` or `linux/arm/v7`, natively on a matching host and under QEMU elsewhere, and inside them an ordinary compiler does an ordinary build. Everything ROS 2 generates works, Python message bindings included. Emulation is the slow part.

The Yocto SDK images are different: a cross toolchain plus the target sysroot, running on the host's architecture. Nothing is emulated, but meta-ros SDKs ship no Python message generator and no `make`, so interface packages get C and C++ code only and the build uses Ninja.

colcon-buildx tells the two apart by the image's labels, not its name. `org.smarobix.buildx.kind` is `oe-sdk` for an SDK image and absent otherwise, and `env-setup` names the SDK script to source. [Image labels](tool/labels.md) is the contract, and it is what lets an image you build yourself work too. Nothing stops you using an image without colcon-buildx, with `docker run` and `colcon build` inside; what you give up is a build owned by your user, kept apart from a host build, and the SDK environment and toolchain wrapper set up for you.

## One middleware: Cyclone DDS

ROS 2 picks its DDS middleware at run time from `RMW_IMPLEMENTATION`. Both Fast DDS and Cyclone DDS are in every install tree here, nothing sets the variable, and unset means Fast DDS. The recommendation is Cyclone DDS on every board, for two reasons. Its memory footprint is markedly smaller, which matters on a 512 MB Pynq and on a 32-bit Pi. And one answer everywhere means no two machines in a fleet that cannot hear each other because they chose differently. Export it in every shell that runs a node, on every machine, your laptop included; for a systemd unit, `Environment=RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`. Packages from older releases recommend Fast DDS on 64-bit boards in their install message; this page is current.

## What is in a `.deb`

The tree is `ros-base` minus the display packages: `rclcpp`, `rclpy`, the `ros2` command line, `launch`, the common interface packages, `tf2`, `urdf`, `robot_state_publisher`, `rosbag2`, `sros2`, both RMW implementations, `cv_bridge` and `image_transport`, plus `demo_nodes_cpp` and the minimal examples for checking a board. `rviz2` and `rqt` are left out; these boards run headless. A package missing from the tree goes into your workspace as source.

The package name is `smarobix-ros-<distro>-<pkg>`, where `<pkg>` names the release the tree was built against (`rpi-trixie`, `rpi-bookworm`, `pynq-v3.1.1`), because the release decides whether the tree runs: trixie and bookworm differ in `libpython`, `libstdc++` and OpenCV. The file name adds the version and the dpkg architecture. `Depends` is computed from what the built binaries link against, so it cannot drift; `Recommends` carries optional features such as `python3-opencv`; `Suggests` is the toolchain for compiling on the board itself, which apt does not install. Upgrade by installing a newer file, remove with `apt remove`.

Two limits. The 32-bit packages are ARMv7, so they run on a Pi 2 and newer and on any ARMv7 Debian board, but not on the ARMv6 Pi 1, Zero and Zero W. And on a Pynq board, `cv_bridge` links an OpenCV that was built into the image under `/opt/install`, which the package neither ships nor declares; check with `ldd /opt/ros/jazzy/lib/libcv_bridge.so | grep 'not found'` before relying on it.

Image tags roll: a tag is rebuilt on every push to `main`, and there are no versioned tags. Pin the digest, which `docker buildx imagetools inspect` prints, when a build has to be reproducible, and take the image and the `.deb` from the same release when it matters.
