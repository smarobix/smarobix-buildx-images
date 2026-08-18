# smarobix-buildx-images

[![Build images](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml/badge.svg)](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml)
[![Latest release](https://img.shields.io/github/v/release/smarobix/smarobix-buildx-images?include_prereleases&sort=semver)](https://github.com/smarobix/smarobix-buildx-images/releases/latest)

CI pipeline that produces two kinds of artifacts for cross-compiling ROS 2 to embedded ARM boards. First, board-specific Docker images that [`smarobix-colcon-buildx`](https://github.com/smarobix/smarobix-colcon-buildx) consumes as its cross-compile environment. Second, ROS 2 install trees for non-Tier-1 boards where the official buildfarm does not publish binaries, packaged as `.deb` archives.

## Why this exists

`armhf` is a Tier 3 architecture in [`REP-2000`](https://www.ros.org/reps/rep-2000.html). The ROS buildfarm does not publish binary apt packages for `armhf` on Humble or Jazzy, which leaves contributors with two bad options: build ROS from source on the board itself (slow, and a stray `apt upgrade` resets it), or build it from source for every workspace (hours per build). This pipeline does the source build once, scopes it to a usable subset, and ships an install tree that drops into `/opt/ros/<distro>` on the board.

For `arm64` boards running **Ubuntu** (Tier 1) the official binaries already exist; the value here is the cross-compile Docker image (toolchain, GStreamer, Xilinx PPAs for Kria, custom OpenCV) so downstream workspaces can build against a known-good environment.

`arm64` alone is not enough, though. Raspberry Pi OS is Debian, and the ROS buildfarm publishes **no** `ros-<distro>-*` binaries for any Debian suite — the `bookworm` and `trixie` dists on `packages.ros.org` carry bootstrap tooling (`ros-dev-tools`, `vcstool`, `rosdep`) and nothing else, against 3361 `ros-jazzy-*` packages for Ubuntu Noble. So the Raspberry Pi targets build from source on *both* architectures and ship a `.deb` for each, even though `arm64` is a Tier-1 architecture. The tier describes the architecture; what matters for packaging is whether binaries exist for the architecture *and* the distribution.

## What is currently built

| Board(s) | Architecture | ROS distros | Artifact | Status |
|---|---|---|---|---|
| Kria K26 | `arm64` | Humble, Jazzy | Cross-compile Docker image | Published |
| Pynq-Z1 / Pynq-Z2 | `armhf` (Cortex-A9, Zynq-7020) | Humble, Jazzy | Cross-compile Docker image + `.deb` of `/opt/ros/<distro>` | Published |
| Raspberry Pi / Debian | `arm64` and `armhf` (ARMv7) | Humble, Jazzy | Docker image + `.deb` of `/opt/ros/<distro>` | New |

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

The recommended RMW is **Cyclone DDS** (`rmw_cyclonedds_cpp`) — it has a markedly smaller memory footprint than Fast DDS, which matters on a Zynq-7020. Note that nothing in the tree forces the choice, so the upstream default (Fast DDS) applies until you `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`; the installed package prints that reminder. Zenoh is not in scope yet because of open ARMv7 issues upstream; once those land, Zenoh will be added.

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
3. More boards as people ask for them.

## Install trees for Raspberry Pi OS / Debian

`dockerfiles/rpi/Dockerfile.{jazzy,humble}` build ROS 2 from source on a Debian base and install into `/opt/ros/<distro>`. Because no ROS binaries exist for Debian, this path is used for **both** `arm64` and `armhf` — unlike the K26 images, which apt-install ROS.

Nothing in these images is Raspberry-Pi-specific: the base is stock Debian, with no Raspberry Pi apt repository or firmware involved. They are named for the runtime they are tested against, but what they produce runs on **any** Debian board of the same suite and architecture. The names carry the ISA baseline rather than a board model for exactly that reason — `rpi-armv7-trixie` is not a Pi-5-only artifact.

A single pair of Dockerfiles covers all eight combinations. The architecture comes from `buildx --platform` (the `debian:*-slim` base is a multi-arch manifest), and the OS release from two build args that must agree:

| `SUITE` | `PY_VER` | Raspberry Pi OS / Debian |
|---|---|---|
| `trixie` | `3.13` | 13 |
| `bookworm` | `3.11` | 12 |

### Which artifact do I want?

Check what the board actually runs — the `.deb`s are not interchangeable across releases, because bookworm and trixie ship different `libpython`, `libstdc++` and OpenCV versions:

```bash
cat /etc/os-release          # VERSION_CODENAME=bookworm or trixie
dpkg --print-architecture    # arm64 or armhf
```

| Image name | `.deb` architecture | Runs on |
|---|---|---|
| `rpi-arm64-<suite>` | `arm64` | Pi 3, 4, 5, Zero 2 W on a 64-bit OS; any arm64 Debian board |
| `rpi-armv7-<suite>` | `armhf` | Pi 2, 3, 4, 5, Zero 2 W on a 32-bit OS; any ARMv7 Debian board |

- Image tags: `rpi-arm64-trixie-jazzy`, `rpi-armv7-bookworm-humble`, and so on
- `.deb` packages: `smarobix-ros-jazzy-rpi-trixie_<version>_arm64.deb` — the architecture is in the filename and the control field, not in the package name, so apt picks the right one

**The 32-bit builds use an ARMv7 baseline** (`--platform linux/arm/v7`, i.e. ARMv7-A with VFPv3). Raspberry Pi OS 32-bit is itself built for ARMv6 so that it still boots a Pi 1, and no maintained Raspbian Docker base image exists any more. The `armhf` `.deb`s therefore run on a Pi 2 and newer but **not** on a Pi 1, Zero, or Zero W.

### OpenCV comes from apt here

Unlike the Pynq and Kria images, which build a specific OpenCV from source because their vendor runtimes demand it, these images use Debian's `libopencv-dev`. `cv_bridge` then links against the very same OpenCV that the board's own apt installs, and the `.deb` can declare a real dependency on it instead of silently needing a `/opt/install` tree that the package does not ship. It also removes the slowest layer of the build.

### Choosing an RMW

Both Fast DDS and Cyclone DDS are built, and nothing in the tree forces a choice, so the upstream default (**Fast DDS**) applies unless you set one.

**Cyclone DDS is the recommendation on memory-constrained boards** — it has a substantially smaller footprint, which is why it is the RMW of choice on the Pynq boards. That maps to the 32-bit builds and to any Pi with 1 GB or less:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

On a Pi 4 or 5 with several gigabytes, either is fine; Fast DDS is the better-tested default. The installed package prints this recommendation for your architecture on install.

### Scope

Same as the Pynq trees: `ros-base` minus display packages, with `cv_bridge`, `image_transport`, and a few `demo_nodes_*` / `examples_rclcpp_minimal_*` packages for sanity-checking on the board.

### Deploy

```bash
# match your board's codename and architecture
wget https://github.com/smarobix/smarobix-buildx-images/releases/latest/download/smarobix-ros-jazzy-rpi-trixie_<version>_arm64.deb
sudo apt install ./smarobix-ros-jazzy-rpi-trixie_<version>_arm64.deb
source /opt/ros/jazzy/setup.bash
```

**Use `apt install ./file.deb`, not `dpkg -i`.** The package declares real dependencies and `dpkg -i` installs none of them. On a Lite board image that difference is the whole ballgame: `dpkg -i` reports success and then `ros2` fails on first use.

Dependencies come in three tiers:

| Tier | Contains | Installed by `apt install ./file.deb` |
|---|---|---|
| `Depends` | Shared libraries the tree links (OpenCV, Boost.Python, libssl, sqlite3, zstd, tinyxml2, …) plus the Python modules without which `ros2` will not start | Yes, required |
| `Recommends` | Optional features: `python3-opencv` for `cv_bridge`'s Python bindings, `python3-cryptography` for `sros2`, `python3-rosdistro` for `ros2doctor` | Yes, by default — remove with `--no-install-recommends` |
| `Suggests` | Toolchain for compiling ROS packages *on* the board | No, install by hand |

The `Depends:` list is not hand-written. It is derived at package time from the built tree's own `DT_NEEDED` entries (see [`CONTRIBUTING.md`](CONTRIBUTING.md#how-deb-dependencies-are-determined)), so it cannot drift from what the binaries actually link against.

To build ROS packages on the board rather than just run them:

```bash
sudo apt install build-essential cmake git python3-dev python3-pip
pip install --break-system-packages 'empy==3.3.4' colcon-common-extensions
```

The empy pin matters: Debian ships empy 4.x, whose API `rosidl` does not support. It is deliberately not a package dependency, since it would collide with Debian's own `python3-empy`. The package prints these instructions on install.

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

```bash
# 64-bit trixie (native on an arm64 host, no emulation)
docker buildx build --platform linux/arm64 \
  --build-arg SUITE=trixie --build-arg PY_VER=3.13 \
  -f dockerfiles/rpi/Dockerfile.jazzy \
  -t rpi-buildx:arm64-trixie-jazzy dockerfiles/rpi

# 32-bit bookworm (emulated, slow)
docker buildx build --platform linux/arm/v7 \
  --build-arg SUITE=bookworm --build-arg PY_VER=3.11 \
  -f dockerfiles/rpi/Dockerfile.jazzy \
  -t rpi-buildx:armv7-bookworm-jazzy dockerfiles/rpi
```

`SUITE` and `PY_VER` must agree (`trixie`/`3.13`, `bookworm`/`3.11`) — the pair sets both the base image and the `PYTHONPATH` of the resulting install tree.

The Pynq and `armhf` builds will take a while (they compile ROS 2 from source under emulation). The `arm64` builds run natively on an Apple Silicon or other `arm64` host and are much faster — roughly 15 minutes for a full tree.

`dockerfiles/rpi/ros-build` sizes colcon's parallelism from available memory rather than core count. Some ROS translation units need well over a gigabyte in `cc1plus`, so one job per core gets the compiler OOM-killed on a machine with less than about 2 GB per core.

## Adding a new board

1. Create `dockerfiles/<board>/Dockerfile.<distro>` (and any `extra.repos.<distro>` files needed by `vcs import`). Existing Dockerfiles are good starting points: `k26/` for boards with apt-installable ROS, `pynq-z1/` for boards that must build from source against a curated vendor image, `rpi/` for boards that must build from source against stock Debian and need to cover several OS releases and architectures from one file.
2. Add an entry to the `matrix.include` list in `.github/workflows/build-images.yml` with the new `(board, distro, platform)` tuple. The workflow takes care of platform setup, registry login, and cache references.
3. Open a PR. The PR build will validate the Dockerfile compiles under QEMU without pushing.

Pick the path by whether ROS apt binaries exist for your board's **architecture *and* distribution**, not by architecture alone — see [`CONTRIBUTING.md`](CONTRIBUTING.md#does-my-board-have-ros-binaries). If they do, copy the K26 path. If they do not, copy the Pynq path (curated vendor image) or the `rpi` path (stock Debian, multiple releases).

## CI

Two GitHub Actions workflows live under `.github/workflows/`:

- **`build-images.yml`** is the main pipeline. One matrix entry per (board, distro, and for Raspberry Pi also OS release and architecture) runs `docker buildx build` with QEMU, against GHCR, with `--cache-from` / `--cache-to` on a `*-buildcache` tag for incremental builds. PRs validate that Dockerfiles still build (no push, no secrets). Pushes to `main` / `develop` and `workflow_dispatch` runs publish to GHCR. On `v*` tags the `package` job extracts every install tree that ships a `.deb` (Pynq and the Debian boards), packages each as `.tar.gz` + `.deb`, and creates a GitHub Release with all of them attached.
- **`dockerhub-mirror.yml`** is a manual (`workflow_dispatch`) mirror to Docker Hub via `docker buildx imagetools create`. It only runs when triggered explicitly and only does anything if `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets are set; otherwise it's inert.

Image tags published to GHCR are rolling: `:<image>-<distro>` from `main`, `:<image>-<distro>-develop` from `develop`. The `<image>` prefix comes from the matrix entry — `k26` for Tier-1 boards (plain Ubuntu base), `pynq-v3.1.1` for Tier-3 boards where the curated downstream version matters, and `rpi-<arch>-<suite>` for the Debian boards, where both the OS release and the architecture change the ABI. Folding the architecture into `<image>` rather than adding a fourth tag component keeps the tag template at `<image>-<distro>`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the rationale. Cutting a `v*` tag does not produce a new image tag, only a `.deb` release.

## Companion repository

[`smarobix-colcon-buildx`](https://github.com/smarobix/smarobix-colcon-buildx) is the colcon extension that consumes the `arm64` Docker images here. If you want to cross-compile a workspace against a K26 image, that is the tool to use. For Pynq boards, install the published `.deb` directly on the board (see the deploy section above) — `smarobix-colcon-buildx` is not needed since the binaries are already built for the board's native architecture.

## License

License to be finalized before public release.
