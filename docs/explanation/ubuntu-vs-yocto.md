# Ubuntu or Yocto

A board here runs ROS 2 in one of two worlds, and they do not mix. Binaries built
against Ubuntu's or Debian's libraries do not run on a Yocto image, and binaries built
against the meta-ros sysroot do not run on Ubuntu. Every target in this repository
belongs to one world or the other, and so does every image.

## The Ubuntu and Debian world

The board runs a general-purpose distribution: Ubuntu on a Kria K26, Raspberry Pi OS or
another Debian on a Pi, Ubuntu 22.04 under the PYNQ image on a Pynq-Z1 or Z2. ROS 2 is
installed on top of it, either from packages.ros.org where those packages exist, or from
a [`.deb` built here](../reference/deb-packages.md) where they do not. It lands in
`/opt/ros/<distro>` and links against the distribution's `libc`, `libpython`, OpenCV and
the rest.

The build images mirror that: the same base distribution and the same ROS 2 packages as
the board.

- `k26-jazzy` is Ubuntu 24.04 with ROS 2 Jazzy `ros-base` from packages.ros.org, plus
  `cv_bridge`, `image_transport`, `vision_msgs` and `v4l2_camera`, the Xilinx PPAs
  (`xilinx-apps/xilinx-drivers`, `ubuntu-xilinx/gstreamer`, `ubuntu-xilinx/sdk`),
  GStreamer (good, bad, libav), `gcc-aarch64-linux-gnu`, and OpenCV 4.10 with the
  contrib modules built from source into `/opt/install`. `k26-humble` is the same idea
  on Ubuntu 22.04, with OpenCV 4.5.0. If your packages use OpenCV, they link against
  that build, so the board needs the same OpenCV on its library path.
- `pynq-v3.1.1-*` and `rpi-*` contain the install tree that the `.deb` ships, so a
  workspace built in them links against exactly what the board has.

Ubuntu is the path of least surprise: apt works, the ROS documentation applies as
written, and a board can be brought up without a Yocto build host.

## The Yocto / meta-ros world

The board runs an image that bitbake built from recipes: kernel, userspace and ROS 2 in
one, from the [`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto)
configuration in this repository on top of [meta-ros](https://github.com/ros/meta-ros).
There is no apt and no ROS 2 to install afterwards; `ros-image-core` already carries
`ros-core`, and an image is what you flash.

That has consequences a first-time user hits immediately:

- There is no package manager on the board. Adding software means rebuilding the image.
- The image has no bash, only BusyBox `ash`, so source `/opt/ros/jazzy/setup.sh` and not
  `setup.bash`.
- The stock configuration logs in as `root` with an empty password, which is meant for a
  bench and nothing else.
- Board images are not published. [colcon-buildx on meta-ros](../tutorials/meta-ros.md)
  and [Rebuilding the Yocto images](../maintain/yocto.md) build them.

In exchange you get an image whose contents are pinned by recipe and reproducible, with
nothing installed that was not asked for, which is what a product image usually has to
be.

Two images are published per Yocto board so that workspaces can be built for them: the
bitbake-built dev container and the SDK image. [Native or cross](native-vs-cross.md)
explains the difference.

## Choosing, and not mixing

- Use the world the board already runs. If the K26 boots Canonical's Ubuntu, use
  `k26-jazzy`; if it boots the image built from `yocto/`, use `k26-yocto-jazzy` or
  `k26-oesdk-jazzy`.
- A workspace can be built for both, but each build has to use the matching image. The
  outputs go in different directories on the board and cannot be swapped.
- If you have not chosen yet: Ubuntu is quicker to start with and easier to change on
  the board; Yocto gives a smaller, pinned image and is the path meta-ros and the wider
  OpenEmbedded tooling assume.

[Pick a target](../how-to/pick-a-target.md) turns this into a per-board answer.
