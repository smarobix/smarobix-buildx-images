---
hide:
  - toc
---

# SMAROBIX buildx

Cross-build your ROS 2 workspace for ARM boards on your own computer, and install ROS 2 on boards that have no official ROS 2 binaries. Every supported board, OS and ROS 2 distro is listed in the [targets reference](reference/targets.md).

smarobix-buildx-images and smarobix-colcon-buildx are two halves of one toolchain. The images repository defines every supported target — board, OS, architecture and ROS 2 distro — and publishes the Docker images and ROS 2 `.deb` packages for them. smarobix-colcon-buildx is the colcon verb that cross-builds your own workspace inside one of those images. To put ROS 2 on a board, use the images repository; to build your code for that board, use colcon-buildx.

## Two separate jobs

Getting your code onto a board takes two jobs. They use different tools, so keep them apart.

1. **Put ROS 2 on the board.** Where ROS 2 comes from depends on the board:
    - Kria K26 with Ubuntu: the official ROS 2 apt packages from packages.ros.org. Nothing from this project goes on the board.
    - Pynq and Raspberry Pi or other Debian boards: a `.deb` package from this project's GitHub releases.
    - Yocto boards: ROS 2 is part of the board image, which you build from `yocto/` in this repository. Board images are not published.
2. **Cross-build your own workspace.** Run `colcon buildx` on your computer with the image that matches the board. This is the same on every target, Pynq included.

## Pick your target

Choose the board, then its OS and architecture where the board offers a choice, then the ROS 2 distro. The picker prints the commands for both jobs.

<div id="buildx-picker" class="buildx-picker" data-targets="targets.json" markdown>

If no picker appears here, every target, image tag and `.deb` file is also listed in the [targets reference](reference/targets.md).

</div>

## Where to go next

<div class="grid cards" markdown>

-   **Tutorials**

    ---

    Start here. [Your first cross-build](tutorials/first-cross-build.md) on a Kria K26, [ROS 2 on a board](tutorials/ros-on-a-board.md) from a `.deb`, and [colcon buildx on a meta-ros image](tutorials/meta-ros.md).

-   **How-to guides**

    ---

    [Pick a target](how-to/pick-a-target.md), [build on an x86_64 host](how-to/build-on-x86_64.md), and [build on the board](how-to/build-on-the-board.md) itself.

-   **Explanation**

    ---

    [Why this exists](explanation/why-this-exists.md), [Ubuntu or Yocto](explanation/ubuntu-vs-yocto.md), [native or cross builds](explanation/native-vs-cross.md), and [why Cyclone DDS](explanation/rmw.md).

-   **Reference**

    ---

    [Targets](reference/targets.md), [deb packages](reference/deb-packages.md) and [tested hardware](reference/tested-hardware.md).

-   **colcon-buildx**

    ---

    The colcon verb: [overview](https://smarobix.github.io/smarobix-buildx-images/tool/), [install](https://smarobix.github.io/smarobix-buildx-images/tool/install/), [usage](https://smarobix.github.io/smarobix-buildx-images/tool/usage/) and [configuration](https://smarobix.github.io/smarobix-buildx-images/tool/config/).

-   **Maintainers**

    ---

    [Add a board](maintain/add-a-board.md), rebuild the images, and cut a release. Start at the [maintainer overview](maintain/index.md).

</div>
