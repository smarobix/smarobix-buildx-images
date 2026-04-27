# buildx-docker-images

CI pipeline that produces two kinds of artifacts for cross-compiling ROS 2 to embedded ARM boards. First, board-specific Docker images that [`colcon-buildx`](https://github.com/smarobix/colcon-buildx) consumes as its cross-compile environment. Second, ROS 2 install trees for non-Tier-1 boards where the official buildfarm does not publish binaries.

## Why this exists

`armhf` is a Tier 3 architecture in [`REP-2000`](https://www.ros.org/reps/rep-2000.html). The ROS buildfarm does not publish binary apt packages for `armhf` on Humble or Jazzy, which leaves contributors with two bad options: build ROS from source on the board itself (slow, and a stray `apt upgrade` resets it), or build it from source for every workspace (hours per build). This pipeline does the source build once, scopes it to a usable subset, and ships an install tree that drops into `/opt/ros/<distro>` on the board.

For `arm64` boards (Tier 1) the official binaries already exist; the value here is the cross-compile Docker image (toolchain, GStreamer, Xilinx PPAs for Kria, custom OpenCV) so downstream workspaces can build against a known-good environment.

## What is currently built

| Board(s) | Architecture | ROS distros | Artifact | Status |
|---|---|---|---|---|
| Kria K26 | `arm64` | Humble, Jazzy | Cross-compile Docker image | Published |
| Pynq-Z1 / Pynq-Z2 | `armhf` (Cortex-A9, Zynq-7020) | Humble, Jazzy | ROS 2 install tree (zip of `/opt/ros/<distro>`) | In progress |

Pynq-Z1 and Pynq-Z2 share the same Zynq-7020 SoC, so a single set of Dockerfiles under `dockerfiles/pynq-z1/` produces an install tree that runs on either board.

Published images live on Docker Hub under `sapertuz/smrbx-buildx`. The migration to a public, namespaced registry is part of an upcoming follow-up; until then, image pulls and CI both go through Docker Hub.

## Cross-compile Docker images (`arm64`)

The Kria K26 images are built from `dockerfiles/k26/Dockerfile.{jazzy,humble}` and pushed on every push to `main`, every push to `develop`, every tag, and on manual web triggers.

```bash
docker pull --platform linux/arm64 sapertuz/smrbx-buildx:kv26-jazzy
docker pull --platform linux/arm64 sapertuz/smrbx-buildx:kv26-humble
```

What's inside (Jazzy variant; Humble is similar):

- Ubuntu 24.04 (Noble) base
- ROS 2 Jazzy `ros-base` plus a small extra set (`cv-bridge`, `image-transport`, `vision-msgs`, `v4l2-camera`)
- Custom OpenCV 4.10 with contrib modules, built for `aarch64`
- GStreamer (good / bad / libav) and Xilinx PPAs (`xilinx-apps/xilinx-drivers`, `ubuntu-xilinx/gstreamer`, `ubuntu-xilinx/sdk`)
- Cross-compile toolchain (`gcc-aarch64-linux-gnu`)

These images are intended to be consumed by [`colcon-buildx`](https://github.com/smarobix/colcon-buildx). You can also pull and run them directly:

```bash
docker run --rm --platform linux/arm64 \
  -v $(pwd):/workspace -w /workspace \
  sapertuz/smrbx-buildx:kv26-jazzy \
  bash -c 'source /opt/ros/jazzy/setup.bash && colcon build --merge-install'
```

## Install trees for `armhf` (Pynq-Z1 / Pynq-Z2)

The Pynq Dockerfiles (`dockerfiles/pynq-z1/Dockerfile.{jazzy,humble}`) build ROS 2 from source on `arm32v7/ubuntu:jammy`, install into `/opt/ros/<distro>`, and produce an install tree that can be deployed to either Pynq-Z1 or Pynq-Z2. The two distro Dockerfiles share build phases so layer caching works across them where possible.

### Scope

The `armhf` install trees are scoped to **`ros-base` minus display-related packages**. Concretely:

- All `ros_base` core: `rclcpp`, `rclpy`, `ros2cli` and its sub-commands, `launch_ros`, `pluginlib`, `class_loader`, the common interface packages (`std_msgs`, `geometry_msgs`, `sensor_msgs`, `nav_msgs`, `action_msgs`, `diagnostic_msgs`, `shape_msgs`, `trajectory_msgs`, `visualization_msgs`)
- `tf2`, `urdf`, `robot_state_publisher`, `rosbag2`, `sros2`
- `cv_bridge` and `image_transport` (built against the in-image OpenCV 4.13)
- A handful of `demo_nodes_*` and `examples_rclcpp_minimal_*` packages for sanity-checking on the board

Display packages (`rviz2`, `rqt`, `rqt_*`, image viewers) are intentionally excluded. They pull in heavy GUI dependencies and Pynq boards typically run headless. If you need them, build them on top of the install tree.

The RMW is **Cyclone DDS** (`rmw_cyclonedds_cpp`). Zenoh is not in scope yet because of open ARMv7 issues upstream; once those land, Zenoh will be added.

### Current artifact and deploy story

This part is in flight. The Pynq-Z1 / Pynq-Z2 Dockerfiles exist and build cleanly. The CI integration that publishes `/opt/ros/<distro>` as a zip archive per (board, distro) build is being wired up right now. Until that lands, the workflow is:

1. Build the image locally:
   ```bash
   docker buildx build --platform linux/arm/v7 \
     -f dockerfiles/pynq-z1/Dockerfile.jazzy \
     -t pynq-jazzy:local dockerfiles/pynq-z1
   ```
2. Extract `/opt/ros/jazzy` from a container and zip it.
3. `rsync` the zip to the board, unpack into `/opt/ros/jazzy`.

Once the CI publishing job lands, steps 1 and 2 collapse into "download the published zip from the registry."

### Roadmap

In rough order:

1. CI job that publishes `<board>-<distro>.zip` (zip of `/opt/ros/<distro>`) on every build.
2. `.deb` packaging of the install tree so it can be `apt install`'d (instead of unzipped).
3. A signed APT repository so contributors can `apt-add-repository` and pull updates the normal way.
4. Zenoh RMW once upstream ARMv7 issues are resolved.
5. More boards as people ask for them. Raspberry Pi 32-bit is the obvious next candidate; an `armhf` Dockerfile already exists as the starting point.

## Building locally

Register QEMU first if you are on `x86_64`:

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Then:

```bash
# arm64 Kria image
docker buildx build --platform linux/arm64 \
  -f dockerfiles/k26/Dockerfile.jazzy \
  -t kria-buildx:k26-jazzy dockerfiles/k26

# armhf Pynq image (slow first time; built from source)
docker buildx build --platform linux/arm/v7 \
  -f dockerfiles/pynq-z1/Dockerfile.jazzy \
  -t pynq-buildx:jazzy dockerfiles/pynq-z1
```

The Pynq build will take a while (it compiles ROS 2 from source under emulation on `x86_64` hosts).

## Adding a new board

1. Create `dockerfiles/<board>/Dockerfile.<distro>` (and any `extra.repos.<distro>` files needed by `vcs import`). Existing Dockerfiles are good starting points: `k26/` for `arm64` boards with apt-installable ROS, `pynq-z1/` for `armhf` boards that have to build from source.
2. Add a job in `.gitlab-ci.yml` mirroring an existing `build:k26-*` block. Set `--platform`, the Dockerfile path, the image tag, and the registry cache refs.
3. Open an MR. We will run a manual pipeline to confirm the image builds.

If the new board is `arm64` with official ROS apt packages available (Tier 1), copy the K26 path. If it is `armhf` or another Tier 3 architecture, copy the Pynq path.

## CI

The pipeline is GitLab CI (`.gitlab-ci.yml`). One job per (board, distro) pair, all running `docker buildx build --push` against the registry, with `--cache-from` and `--cache-to` against a `*-buildcache` tag for incremental builds. Triggers: push to `main`, push to `develop`, git tags, manual web triggers. Public CI (and the corresponding public registry) is on the upcoming migration list.

## Companion repository

[`colcon-buildx`](https://github.com/smarobix/colcon-buildx) is the colcon extension that consumes the `arm64` Docker images here. If you want to cross-compile a workspace against a K26 image, that is the tool to use. Once the `armhf` install-tree zips are being published, `colcon-buildx` (or plain `rsync`) is also how you deploy them to a Pynq board.

## License

License to be finalized before public release.
