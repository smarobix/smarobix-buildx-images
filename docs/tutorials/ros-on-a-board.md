# Put ROS 2 on a board from a .deb

Raspberry Pi OS and Debian have no ROS 2 packages of their own: the ROS buildfarm
publishes none for any Debian release ([why](../explanation/why-this-exists.md)). This
repository builds the install tree once and ships it as a `.deb`, so a board gets ROS 2
with one `apt install` instead of an afternoon of compiling.

This tutorial installs ROS 2 Jazzy on a 64-bit Raspberry Pi OS 13 (trixie) board and
runs the talker and listener demo. The same steps work on a Pynq board and on any other
Debian board; see [Other boards and other distros](#other-boards-and-other-distros).

## What you need

- A Raspberry Pi 3, 4, 5 or Zero 2 W running Raspberry Pi OS 13 (trixie), 64-bit. Lite
  is fine; nothing here needs a desktop.
- Network access from the board, and `sudo`.

## 1. Check what the board runs

The packages are built against one Debian release and one architecture and are not
interchangeable: the releases ship different `libpython`, `libstdc++` and OpenCV
versions. Ask the board:

```bash
. /etc/os-release && echo "$VERSION_CODENAME"   # trixie
dpkg --print-architecture                       # arm64
```

If you get something other than `trixie` and `arm64`, read
[Other boards and other distros](#other-boards-and-other-distros) before you download.

## 2. Install the package

```bash
wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v1.1.0/smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
sudo apt install ./smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
```

Use `apt install ./<file>.deb`, not `dpkg -i`. The package declares real dependencies,
and `dpkg -i` installs none of them: on a Lite image it reports success and then `ros2`
fails on first use. The leading `./` is what tells apt the argument is a file.

apt may print a note that the download is performed unsandboxed as root, because the
`_apt` user cannot read a file in your home directory. It is harmless for a local file.

The tree lands in `/opt/ros/jazzy`. The package prints a short summary when it is
configured. In v1.1.0 that summary recommends Fast DDS on 64-bit boards and suggests a
`pip` command for building packages on the board; both are out of date. Use Cyclone DDS
as below, and [Build on the board](../how-to/build-on-the-board.md) for the build tools.

## 3. Set up the shell

```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

Both Fast DDS and Cyclone DDS are in the tree and nothing sets `RMW_IMPLEMENTATION`, so
you choose. Cyclone DDS is the recommendation on every target here
([why](../explanation/rmw.md)).

To get both in every new shell:

```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
```

## 4. Run the demo

The tree includes `demo_nodes_cpp` for exactly this check. In one shell:

```bash
ros2 run demo_nodes_cpp talker
```

In a second shell, after the same two setup lines:

```bash
ros2 run demo_nodes_cpp listener
```

The talker prints `Publishing: 'Hello World: 1'` once a second and the listener prints
`I heard: [Hello World: 1]`. Both shells need the same `RMW_IMPLEMENTATION`; nodes
using different RMW implementations are not guaranteed to hear each other.

`ros2 topic list` and `ros2 node list` work as usual. [What is in the
package](../reference/deb-packages.md#what-is-in-the-tree) lists the rest.

## Other boards and other distros

The [target picker](https://smarobix.github.io/smarobix-buildx-images/) prints the exact
download line for a board, OS, architecture and ROS distro. To work it out yourself, ask
the board the same two questions as in step 1 and assemble the file name:

```text
smarobix-ros-<distro>-<pkg>_1.1.0_<deb_arch>.deb
```

- `<distro>` is `jazzy` or `humble`.
- `<pkg>` is `rpi-` plus the codename on Raspberry Pi OS and Debian (`rpi-bookworm`,
  `rpi-trixie`), or `pynq-v3.1.1` on a board running the PYNQ v3.1.1 image.
- `<deb_arch>` is the output of `dpkg --print-architecture`: `arm64` or `armhf`. The
  Pynq packages are `armhf` only.
- `1.1.0` is the current release, `v1.1.0`, without the `v`.

The download URL is always
`https://github.com/smarobix/smarobix-buildx-images/releases/download/v1.1.0/<file>`.
Do not use a `releases/latest` link: the release stream also carries the Yocto SDK
releases, so "latest" is not always the newest `.deb` release.

Two limits are worth knowing before you download:

- The 32-bit packages are built for ARMv7. They run on a Pi 2 and newer, and on any
  other ARMv7 Debian board, but not on a Pi 1, Zero or Zero W, which are ARMv6.
- A Kria K26 on Ubuntu needs no package from here. Install the official ROS 2 packages
  from packages.ros.org; step 1 of
  [Cross-build your first workspace](first-cross-build.md) shows how.

[Pick a target](../how-to/pick-a-target.md) has the full decision, and
[.deb packages](../reference/deb-packages.md) the naming rules and dependency tiers.

## Next steps

- Build your own workspace for this board on your computer and copy the result over:
  [Cross-build your first workspace](first-cross-build.md), with this `.buildx.conf`:

  ```ini
  method = docker
  docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy
  docker_platform = linux/arm64
  ```

  The image holds the same install tree as the package you just installed.
- To compile ROS packages on the board itself, follow
  [Build on the board](../how-to/build-on-the-board.md).
- To remove the package: `sudo apt remove smarobix-ros-jazzy-rpi-trixie`. To move to a
  newer release, install its `.deb` the same way; apt treats it as an upgrade.
