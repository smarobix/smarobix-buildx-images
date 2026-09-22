# Cross-build your first workspace for a Kria K26

This tutorial cross-builds a small ROS 2 workspace on your computer, copies it to a
Kria KV260 or KR260 running Ubuntu, and runs it there. It does the two jobs in order:
ROS 2 goes on the board from the official packages, then `colcon buildx` builds your own
code in the matching image.

It uses ROS 2 Jazzy on Ubuntu 24.04. For Ubuntu 22.04 use Humble instead: replace
`jazzy` with `humble` everywhere, including the image tag `k26-humble` and the branch
of the examples repository.

## What you need

- A computer with Docker and Python 3. The image is `linux/arm64`, so it runs natively
  on arm64 Linux and on an Apple Silicon Mac. On an x86_64 host, register QEMU first;
  see [Build on an x86_64 host](../how-to/build-on-x86_64.md).
- `git` and `rsync` on that computer.
- A KV260 or KR260 running Ubuntu 24.04, reachable over SSH. The commands below use
  `ubuntu@10.42.0.3`; use your board's user name and address.

## 1. Put ROS 2 on the board

On a K26 running Ubuntu, ROS 2 comes from the official packages on packages.ros.org.
Nothing from this project goes on the board. Run this on the board:

```bash
sudo apt install software-properties-common curl
sudo add-apt-repository universe
ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | cut -d'"' -f4)
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo "$VERSION_CODENAME")_all.deb"
sudo apt install /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install ros-jazzy-ros-base ros-jazzy-rmw-cyclonedds-cpp rsync
```

This is the [official installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html),
with two additions: `ros-jazzy-rmw-cyclonedds-cpp` is the RMW this project recommends
on every target ([why](../explanation/rmw.md)), and `rsync` is what step 6 deploys with.

Check the result on the board:

```bash
source /opt/ros/jazzy/setup.bash
ros2 pkg list | head -n 3
```

## 2. Install colcon-buildx

On your computer:

```bash
python3 -m venv ~/.venvs/buildx
. ~/.venvs/buildx/bin/activate
pip install "git+https://github.com/smarobix/smarobix-colcon-buildx"
colcon buildx --help
```

The virtual environment keeps colcon-buildx out of the system Python, which recent
Debian, Ubuntu and Homebrew installations refuse to let pip modify.
[Install](https://smarobix.github.io/smarobix-buildx-images/tool/install/) covers the
other ways.

## 3. Create a workspace

Two packages from the official ROS 2 examples, a publisher and a subscriber:

```bash
mkdir -p ~/k26_ws/src && cd ~/k26_ws
git clone -b jazzy --depth 1 https://github.com/ros2/examples.git src/examples
```

## 4. Point colcon-buildx at the K26 image

Create `.buildx.conf` in the workspace root, the directory that holds `src/`:

```ini
method = docker
docker_image = ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy
docker_platform = linux/arm64
deploy_target = ubuntu@10.42.0.3:~/ros2_ws/install/
```

`k26-jazzy` is the image for a K26 running Ubuntu with Jazzy. It is Ubuntu 24.04 with
ROS 2 from the same official packages as the board, plus a cross toolchain, GStreamer,
the Xilinx PPAs and an OpenCV build, so what you build links against the libraries the
board has. [Pick a target](../how-to/pick-a-target.md) covers the other boards, and
[Config](https://smarobix.github.io/smarobix-buildx-images/tool/config/) the other keys.

## 5. Build

```bash
colcon buildx --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber \
  --cmake-args -DBUILD_TESTING=OFF
```

The first run pulls the image, which takes a few minutes. colcon-buildx then runs
`colcon build --merge-install` inside it and passes on the arguments it does not handle
itself, such as `--packages-select` and `--cmake-args`. `-DBUILD_TESTING=OFF` skips the
examples' tests and linters, which you do not need on the board.

The result lands in `cross_build/` and `cross_install/`, owned by you and kept apart
from a native `build/` and `install/`. Check that it is a board binary:

```bash
file cross_install/lib/examples_rclcpp_minimal_publisher/publisher_member_function
```

The output says `ELF 64-bit LSB` and `ARM aarch64`.

## 6. Deploy

Create the target directory on the board once, then build again with `--deploy`:

```bash
ssh ubuntu@10.42.0.3 mkdir -p ros2_ws/install
colcon buildx --deploy --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber \
  --cmake-args -DBUILD_TESTING=OFF
```

The build has nothing left to do, so it finishes quickly and then rsyncs
`cross_install/` to `deploy_target`. Run it from the workspace root.

Deploy uses `rsync --delete`: anything in `~/ros2_ws/install/` on the board that the
build did not produce is removed. Point `deploy_target` at a directory that holds
nothing else. See
[Sync and deploy](https://smarobix.github.io/smarobix-buildx-images/tool/sync-and-deploy/).

## 7. Run it on the board

In one shell on the board:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 run examples_rclcpp_minimal_publisher publisher_member_function
```

In a second shell on the board, with the same three setup lines:

```bash
ros2 run examples_rclcpp_minimal_subscriber subscriber_member_function
```

The publisher prints `Publishing: 'Hello, world! 0'` and counts up; the subscriber
prints `I heard: 'Hello, world! 0'` for each message. Both shells need the same
`RMW_IMPLEMENTATION`.

## Next steps

- Build your own packages the same way: put them in `src/` and drop `--packages-select`.
- If your packages need apt dependencies, `--install-deps-on-device` installs them on
  the board and `--sync-from-device` matches the image's package versions to it. See
  [Sync and deploy](https://smarobix.github.io/smarobix-buildx-images/tool/sync-and-deploy/).
- For a Pynq, a Raspberry Pi or another Debian board, [Pick a target](../how-to/pick-a-target.md)
  gives the image tag and the `.deb`; the rest of this tutorial is unchanged.
- For a K26 running a Yocto image rather than Ubuntu, follow
  [colcon-buildx on meta-ros](meta-ros.md). Binaries built here do not run there.
