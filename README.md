# smarobix-buildx-images

[![Build images](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml/badge.svg)](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml)
[![Latest release](https://img.shields.io/github/v/release/smarobix/smarobix-buildx-images?include_prereleases&sort=semver)](https://github.com/smarobix/smarobix-buildx-images/releases/latest)

CI pipeline that produces two kinds of artifacts for cross-compiling ROS 2 to embedded ARM boards. First, board-specific Docker images that [`smarobix-colcon-buildx`](https://github.com/smarobix/smarobix-colcon-buildx) consumes as its cross-compile environment. Second, ROS 2 install trees for non-Tier-1 boards where the official buildfarm does not publish binaries, packaged as `.deb` archives.

## Why this exists

`armhf` is a Tier 3 architecture in [`REP-2000`](https://www.ros.org/reps/rep-2000.html). The ROS buildfarm does not publish binary apt packages for `armhf` on Humble or Jazzy, which leaves contributors with two bad options: build ROS from source on the board itself (slow, and a stray `apt upgrade` resets it), or build it from source for every workspace (hours per build). This pipeline does the source build once, scopes it to a usable subset, and ships an install tree that drops into `/opt/ros/<distro>` on the board.

For `arm64` boards (Tier 1) the official binaries already exist; the value here is the cross-compile Docker image (toolchain, GStreamer, Xilinx PPAs for Kria, custom OpenCV) so downstream workspaces can build against a known-good environment.

## What is currently built

| Board(s) | Architecture | ROS distros | Artifact | Status |
|---|---|---|---|---|
| Kria K26 | `arm64` | Humble, Jazzy | Cross-compile Docker image | Published |
| Pynq-Z1 / Pynq-Z2 | `armhf` (Cortex-A9, Zynq-7020) | Humble, Jazzy | Cross-compile Docker image + `.deb` of `/opt/ros/<distro>` | Published |

Pynq-Z1 and Pynq-Z2 share the same Zynq-7020 SoC, so a single set of Dockerfiles under `dockerfiles/pynq-z1/` produces an install tree that runs on either board.

Published images live on GHCR under [`ghcr.io/smarobix/smarobix-buildx-images`](https://github.com/smarobix/smarobix-buildx-images/pkgs/container/smarobix-buildx-images). A Docker Hub mirror at `sapertuz/smarobix-buildx` is updated manually for users who prefer that registry.

## Cross-compile Docker images (`arm64`)

The Kria K26 images are built from `dockerfiles/k26/Dockerfile.{jazzy,humble}` and pushed on every push to `main`, every push to `develop`, and on manual workflow runs.

```bash
docker pull --platform linux/arm64 ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy
docker pull --platform linux/arm64 ghcr.io/smarobix/smarobix-buildx-images:k26-humble
```

What's inside (Jazzy variant; Humble is similar):

- Ubuntu 24.04 (Noble) base
- ROS 2 Jazzy `ros-base` plus a small extra set (`cv-bridge`, `image-transport`, `vision-msgs`, `v4l2-camera`)
- Custom OpenCV 4.10 with contrib modules, built for `aarch64`
- GStreamer (good / bad / libav) and Xilinx PPAs (`xilinx-apps/xilinx-drivers`, `ubuntu-xilinx/gstreamer`, `ubuntu-xilinx/sdk`)
- Cross-compile toolchain (`gcc-aarch64-linux-gnu`)

These images are intended to be consumed by [`smarobix-colcon-buildx`](https://github.com/smarobix/smarobix-colcon-buildx). You can also pull and run them directly:

```bash
docker run --rm --platform linux/arm64 \
  -v $(pwd):/workspace -w /workspace \
  ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy \
  bash -c 'source /opt/ros/jazzy/setup.bash && colcon build --merge-install'
```

## Install trees for `armhf` (Pynq-Z1 / Pynq-Z2)

The Pynq Dockerfiles (`dockerfiles/pynq-z1/Dockerfile.{jazzy,humble}`) build ROS 2 from source on `arm32v7/ubuntu:jammy`, install into `/opt/ros/<distro>`, and produce an install tree that can be deployed to either Pynq-Z1 or Pynq-Z2. The two distro Dockerfiles share build phases so layer caching works across them where possible.

### Compatibility

These images and `.deb` packages are built and tested against the **PYNQ v3.1.1 SD-card image** (Ubuntu 22.04). The Docker base image (`arm32v7/ubuntu:jammy`) is intentionally chosen to match the PYNQ runtime, so binaries link against the same C library, Python, and OpenCV versions present on the board.

The PYNQ version is encoded in the image tag and `.deb` package name:

- Image tags: `pynq-v3.1.1-jazzy`, `pynq-v3.1.1-humble`
- `.deb` packages: `smarobix-ros-jazzy-pynq-v3.1.1`, `smarobix-ros-humble-pynq-v3.1.1`

When PYNQ ships a new release, a new image variant is added rather than overwriting the existing one — both can coexist so users on different SD-card images get the right binaries. Check the [PYNQ releases page](https://github.com/Xilinx/PYNQ/releases) for the version on your board. Guidance for adding a new target version is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Scope

The `armhf` install trees are scoped to **`ros-base` minus display-related packages**. Concretely:

- All `ros_base` core: `rclcpp`, `rclpy`, `ros2cli` and its sub-commands, `launch_ros`, `pluginlib`, `class_loader`, the common interface packages (`std_msgs`, `geometry_msgs`, `sensor_msgs`, `nav_msgs`, `action_msgs`, `diagnostic_msgs`, `shape_msgs`, `trajectory_msgs`, `visualization_msgs`)
- `tf2`, `urdf`, `robot_state_publisher`, `rosbag2`, `sros2`
- `cv_bridge` and `image_transport` (built against the in-image OpenCV 4.13)
- A handful of `demo_nodes_*` and `examples_rclcpp_minimal_*` packages for sanity-checking on the board

Display packages (`rviz2`, `rqt`, `rqt_*`, image viewers) are intentionally excluded. They pull in heavy GUI dependencies and Pynq boards typically run headless. If you need them, build them on top of the install tree.

The RMW is **Cyclone DDS** (`rmw_cyclonedds_cpp`). Zenoh is not in scope yet because of open ARMv7 issues upstream; once those land, Zenoh will be added.

### Current artifact and deploy story

The Pynq Dockerfiles are built on every push to `main`/`develop` and pushed to GHCR alongside the K26 images. On every `v*` git tag, a release job additionally extracts `/opt/ros/<distro>` from the freshly built image, packages it as both `.tar.gz` and `.deb`, and attaches them to a GitHub Release.

To deploy on a board:

```bash
# pick the latest release for your distro and PYNQ version
wget https://github.com/smarobix/smarobix-buildx-images/releases/latest/download/smarobix-ros-jazzy-pynq-v3.1.1_<version>_armhf.deb
sudo dpkg -i smarobix-ros-jazzy-pynq-v3.1.1_<version>_armhf.deb
# install tree lands at /opt/ros/jazzy
source /opt/ros/jazzy/setup.bash
```

The corresponding `.tar.gz` is also attached to the release for users who prefer to drop the tree in by hand or rsync it to a board without root.

### Roadmap

In rough order:

1. A signed APT repository so contributors can `apt-add-repository` and pull updates the normal way (instead of `wget` + `dpkg -i`).
2. Zenoh RMW once upstream ARMv7 issues are resolved.
3. More boards as people ask for them. Raspberry Pi 32-bit is the obvious next candidate; an `armhf` Dockerfile already exists as the starting point.

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
2. Add an entry to the `matrix.include` list in `.github/workflows/build-images.yml` with the new `(board, distro, platform)` tuple. The workflow takes care of platform setup, registry login, and cache references.
3. Open a PR. The PR build will validate the Dockerfile compiles under QEMU without pushing.

If the new board is `arm64` with official ROS apt packages available (Tier 1), copy the K26 path. If it is `armhf` or another Tier 3 architecture, copy the Pynq path.

## CI

Two GitHub Actions workflows live under `.github/workflows/`:

- **`build-images.yml`** is the main pipeline. One matrix entry per (board, distro) pair runs `docker buildx build` with QEMU, against GHCR, with `--cache-from` / `--cache-to` on a `*-buildcache` tag for incremental builds. PRs validate that Dockerfiles still build (no push, no secrets). Pushes to `main` / `develop` and `workflow_dispatch` runs publish to GHCR. On `v*` tags an extra job extracts the Pynq install trees, packages them as `.tar.gz` + `.deb`, and creates a GitHub Release with both attached.
- **`dockerhub-mirror.yml`** is a manual (`workflow_dispatch`) mirror to Docker Hub via `docker buildx imagetools create`. It only runs when triggered explicitly and only does anything if `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets are set; otherwise it's inert.

Image tags published to GHCR are rolling: `:<image>-<distro>` from `main`, `:<image>-<distro>-develop` from `develop`. The `<image>` prefix comes from the matrix entry — `k26` for Tier-1 boards (plain Ubuntu base), `pynq-v3.1.1` for Tier-3 boards where the curated downstream version matters. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the rationale. Cutting a `v*` tag does not produce a new image tag, only a `.deb` release.

## Companion repository

[`smarobix-colcon-buildx`](https://github.com/smarobix/smarobix-colcon-buildx) is the colcon extension that consumes the `arm64` Docker images here. If you want to cross-compile a workspace against a K26 image, that is the tool to use. For Pynq boards, install the published `.deb` directly on the board (see the deploy section above) — `smarobix-colcon-buildx` is not needed since the binaries are already built for the board's native architecture.

## License

License to be finalized before public release.
