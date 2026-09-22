# .deb packages

Two families of target ship a ROS 2 install tree as a Debian package: the Pynq boards
and the Raspberry Pi OS / Debian boards. Those are the ones with no ROS 2 binaries
upstream ([why](../explanation/why-this-exists.md)). The Kria K26 on Ubuntu installs
ROS 2 from packages.ros.org instead, and Yocto boards have it in the board image, so
neither ships a package here.

Each package is attached to a GitHub release, together with a `.tar.gz` of the same
tree for dropping in by hand or rsyncing to a board without root.

## Names and versions

```text
smarobix-ros-<distro>-<pkg>_<version>_<deb_arch>.deb
```

| Field | Meaning | Values |
|---|---|---|
| `<distro>` | ROS 2 distro | `jazzy`, `humble` |
| `<pkg>` | the target the tree was built against | `pynq-v3.1.1`, `rpi-bookworm`, `rpi-trixie` |
| `<version>` | the release tag without the `v` | `1.1.0` for release `v1.1.0` |
| `<deb_arch>` | dpkg architecture of the board | `arm64`, `armhf` |

The package name — the `Package:` control field — is `smarobix-ros-<distro>-<pkg>`, with
no architecture in it. dpkg already carries the architecture in the file name and in the
`Architecture:` field, which is what lets apt pick the right file. So
`smarobix-ros-jazzy-rpi-trixie` ships as both `_arm64.deb` and `_armhf.deb`.

`<pkg>` carries the OS release rather than the board model, because the release is what
decides whether the tree runs: `rpi-trixie` is any Debian 13 board, not only a Pi. The
Pynq packages carry the PYNQ version for the same reason.

The current release is **v1.1.0**, so the version field is `1.1.0`. A complete example:

```text
smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
```

## Downloading

```text
https://github.com/smarobix/smarobix-buildx-images/releases/download/v1.1.0/<file>
```

Always link to a tag, not to `releases/latest/download/...`. The Yocto SDK releases
share the same release stream, so "latest" can point at a release that has no `.deb`
files in it at all, and every `latest` link would then return 404.

The [target picker](https://smarobix.github.io/smarobix-buildx-images/) builds the whole
line for a given board, OS, architecture and distro.

## Installing

```bash
sudo apt install ./smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
```

Use `apt install ./<file>.deb`, never `dpkg -i`. The package declares real dependencies
and `dpkg -i` installs none of them: on a minimal board image it reports success and
then `ros2` fails on first use. The leading `./` is how apt knows the argument is a file
and not a package name.

The tree installs into `/opt/ros/<distro>`, and nothing else on the system is touched.

- Upgrade: install the newer release's file the same way; apt sees a higher version.
- Remove: `sudo apt remove smarobix-ros-<distro>-<pkg>`.
- Several distros can be installed side by side; they occupy different directories and
  have different package names.

[Put ROS 2 on a board from a .deb](../tutorials/ros-on-a-board.md) is the whole sequence
on a real board.

## Dependency tiers

| Tier | Contains | Installed by `apt install ./file.deb` |
|---|---|---|
| `Depends` | The shared libraries the tree links against (OpenCV, Boost.Python, libssl, sqlite3, zstd, tinyxml2, libyaml and the rest) plus the Python modules without which `ros2` will not start: `python3`, `python3-argcomplete`, `python3-lark`, `python3-numpy`, `python3-packaging`, `python3-psutil`, `python3-yaml`, and `python3-netifaces` on Humble | Yes, required |
| `Recommends` | Optional features: `python3-opencv` for `cv_bridge`'s Python bindings, `python3-cryptography` for `sros2`, `python3-rosdistro` for `ros2doctor`, `python3-catkin-pkg`, `python3-lxml` | Yes, by default; opt out with `--no-install-recommends` |
| `Suggests` | The toolchain for compiling ROS packages *on* the board | No. See [Build ROS packages on the board](../how-to/build-on-the-board.md) |

The `Depends:` list is not hand-written: it is derived at package time from what the
built tree's own ELF objects link against, so it cannot drift from the binaries.
[How Depends is computed](../maintain/deb-dependencies.md) describes the derivation and
the three hand-kept fields.

Two things are deliberately not dependencies:

- **Test and lint tooling** (`pytest`, `flake8`, `mypy` and friends), which comes from
  `ament_*` packages and is not needed to run nodes.
- **empy**, which is only used to generate interface code. It belongs to the on-board
  build tools, where it is installed from apt as `python3-empy`.

## What the package prints when it is configured

`Suggests` are invisible during a normal install, and so is the middleware choice, so
the package prints both in its `postinst`: where it installed, the `source` line, the
recommended `RMW_IMPLEMENTATION`, and how to get the tools for building packages on the
board.

The packages in release v1.1.0 print two pieces of advice that have since changed: they
recommend Fast DDS on the `arm64` packages, and they suggest installing empy with pip.
Follow [Why Cyclone DDS](../explanation/rmw.md) and
[Build ROS packages on the board](../how-to/build-on-the-board.md) instead.

## What is in the tree

The scope is **`ros-base` minus the display packages**, plus a few extras for checking
the installation on the board. The same set on every `.deb` target:

- The `ros_base` core: `rclcpp`, `rclpy`, `ros2cli` and its sub-commands (`ros2topic`,
  `ros2node`, `ros2service`, `ros2param`, `ros2action`, `ros2run`, `ros2launch`,
  `ros2component`, `ros2pkg`, `ros2interface`, `ros2doctor`, `ros2lifecycle`,
  `ros2multicast`, `ros2plugin`), `launch_ros` with the XML, YAML and testing
  extensions, `pluginlib` and `class_loader`.
- The common interface packages: `std_msgs`, `std_srvs`, `geometry_msgs`,
  `sensor_msgs`, `nav_msgs`, `action_msgs`, `actionlib_msgs`, `diagnostic_msgs`,
  `shape_msgs`, `stereo_msgs`, `trajectory_msgs`, `visualization_msgs`.
- `tf2` (`tf2_ros`, `tf2_geometry_msgs`, `tf2_sensor_msgs`, `tf2_eigen`, `tf2_tools`),
  `urdf`, `kdl_parser`, `robot_state_publisher`, `rosbag2` (`ros2bag`,
  `rosbag2_transport`), `sros2`, `rclcpp_action`, `rclcpp_lifecycle`.
- Both middleware implementations, `rmw_fastrtps_cpp` and `rmw_cyclonedds_cpp`. Neither
  is selected for you; see [Why Cyclone DDS](../explanation/rmw.md).
- `cv_bridge` and `image_transport`.
- For checking the board: `demo_nodes_cpp` (the talker and listener) and
  `examples_rclcpp_minimal_client`, `_publisher`, `_service`, `_subscriber`, `_timer`.

Display packages — `rviz2`, `rqt`, the `rqt_*` plugins, the image viewers — are left out
on purpose. They pull in heavy GUI dependencies and these boards usually run headless.
Build them on top of the tree if you need them.

## OpenCV

Where OpenCV comes from differs by target, and it matters if you use `cv_bridge`.

- **Raspberry Pi OS / Debian:** from Debian, `libopencv-dev`. `cv_bridge` links the very
  same OpenCV that the board's own apt installs, so the package declares a real
  dependency on it and apt installs it with the package. This is also the cheapest
  option to build.
- **Pynq:** built from source in the image, OpenCV 4.13 with the contrib modules, under
  `/opt/install`. The PYNQ runtime dictates the version. The package contains
  `/opt/ros/<distro>` only, so that OpenCV is not shipped with it and no Debian package
  owns it to depend on. If you use `cv_bridge` on a Pynq board, check that it resolves:
  `ldd /opt/ros/jazzy/lib/libcv_bridge.so | grep 'not found'`.
- **Kria K26:** built from source in the image as well (4.10 for Jazzy, 4.5.0 for
  Humble), for the same reason. No `.deb` is shipped for the K26; what this means for a
  workspace you cross-build is in [Ubuntu or Yocto](../explanation/ubuntu-vs-yocto.md).

## The 32-bit packages are ARMv7

The `armhf` builds use `--platform linux/arm/v7`, that is ARMv7-A with VFPv3. Raspberry
Pi OS 32-bit is itself built for ARMv6 so that it still boots a Pi 1, and no maintained
Raspbian Docker base image exists any more to build against.

So an `armhf` package here runs on a Pi 2 and newer, on a Pi 3, 4, 5 or Zero 2 W running
a 32-bit OS, and on any other ARMv7 Debian board. It does **not** run on a Pi 1, Zero or
Zero W.

## Debian releases

The tree is built against one release and is not portable across them: `libpython`,
`libstdc++` and the OpenCV sonames all differ.

| Codename | Raspberry Pi OS / Debian | Python |
|---|---|---|
| `trixie` | 13 | 3.13 |
| `bookworm` | 12 | 3.11 |

Check the board with `. /etc/os-release && echo "$VERSION_CODENAME"`.

## PYNQ versions

The Pynq images and packages are built against the **PYNQ v3.1.1 SD-card image**
(Ubuntu 22.04), and the Docker base (`arm32v7/ubuntu:jammy`) is chosen to match it, so
the binaries link against the same C library, Python and OpenCV the board runs.

The PYNQ version is therefore part of the name, in the image tag
(`pynq-v3.1.1-jazzy`, `pynq-v3.1.1-humble`) and in the package name
(`smarobix-ros-jazzy-pynq-v3.1.1`, `smarobix-ros-humble-pynq-v3.1.1`). When PYNQ
publishes a new release, a new variant is added rather than the existing one being
overwritten, so boards on different SD-card images keep getting the right binaries.
Check which release your card was written from on the
[PYNQ releases page](https://github.com/Xilinx/PYNQ/releases), and see
[Add a downstream version](../maintain/add-a-downstream-version.md) for adding one.

Pynq-Z1 and Pynq-Z2 share the Zynq-7020 SoC, so one package serves both.

## Where the tree comes from

Each package is extracted from the image of the same target, built by CI from the ROS 2
source listed in `ros2/ros2`'s repos file for that distro, plus `vision_opencv` (which
is where `cv_bridge` lives) and `vision_msgs`. Two fixes are applied to the Debian
builds for source that predates the toolchains Debian now ships:

- Humble's vendored pybind11 is raised from 2.9.1 to 2.13.6, because 2.9.1 does not
  build against Python 3.11 or 3.13.
- Humble's `mcap_vendor` is built without `-Werror`, which matches what Jazzy ships;
  bookworm's GCC 12 otherwise fails the build on a warning.

Image tags are rolling and there are no versioned image tags, so an image pulled today
can be newer than the tree inside an older release's `.deb`. Take both from the same
release where that matters.

## Planned

A signed apt repository, so that a board can add it once and get updates through apt
rather than downloading a file per release. Until then each release is a download.
