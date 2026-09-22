# Build ROS packages on the board

You need this only to *compile* ROS packages on the board itself. Running nodes from an
installed `.deb` needs nothing beyond the package: the compiler, CMake and colcon are
listed as `Suggests`, which apt does not install.

Building on the board is slow compared with cross-building on a computer
([Cross-build your first workspace](../tutorials/first-cross-build.md)), but it needs no
second machine and no Docker.

The instructions below are for a board that got ROS 2 from a `.deb` here: Raspberry Pi
OS or Debian (bookworm, trixie) and PYNQ v3.1.1 (Ubuntu jammy). On a K26 running Ubuntu,
ROS 2 and its build tools both come from packages.ros.org; follow the
[official documentation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
instead.

## Install the build tools

```bash
# add the ROS 2 apt source (official method, works on bookworm, trixie and jammy)
sudo apt install curl
ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | cut -d'"' -f4)
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo "$VERSION_CODENAME")_all.deb"
sudo apt install /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install ros-dev-tools python3-empy build-essential cmake git python3-dev
```

`ros-dev-tools` brings colcon, rosdep, vcstool and the rest of the ROS bootstrap
tooling. packages.ros.org publishes it for bookworm, trixie and jammy, and it works on
both `armhf` and `arm64`. The ament build system itself is already in
`/opt/ros/<distro>`.

## Build a workspace

```bash
source /opt/ros/jazzy/setup.bash
cd ~/my_ws
colcon build --merge-install
source install/setup.bash
```

Use the distro the board has: `humble` in place of `jazzy` if that is what you
installed.

## Why there is no pip in these instructions

Everything above comes from apt, on purpose.

- **empy.** Debian bookworm and trixie and Ubuntu jammy all ship `python3-empy` 3.3.4,
  which is the version `rosidl` supports. empy 4.x is only in Debian experimental, so
  there is nothing to pin around and no reason to install it with pip. Older versions of
  this documentation, and the message printed by the v1.1.0 packages, claimed otherwise.
- **The system Python is externally managed.** Debian and Ubuntu mark it so (PEP 668),
  and installing into it with pip anyway would put files beside apt-managed modules and
  can break them. A virtual environment is the supported way to use pip there, but none
  of these tools need one.
- **Nothing collides with `/opt/ros/<distro>`.** The ROS 2 apt source's Debian dists, and
  its jammy `armhf` dist, carry no `ros-<distro>-*` packages at all; they carry the
  bootstrap tooling. Adding the source cannot pull a second ROS 2 onto the board.

## What apt cannot give you

packages.ros.org publishes no `ros-<distro>-*` binaries for any Debian release, or for
`armhf` on Ubuntu. So `rosdep install` can resolve system dependencies such as
`libopencv-dev`, but it cannot install ROS packages that are missing from
`/opt/ros/<distro>`: add those to your workspace as source and build them with your own
packages. [What is in the tree](../reference/deb-packages.md#what-is-in-the-tree) lists
what is already there.
