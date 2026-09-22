# smarobix-buildx-images

[![Build images](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml/badge.svg)](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml)
[![Latest release](https://img.shields.io/github/v/release/smarobix/smarobix-buildx-images?include_prereleases&sort=semver&filter=v*)](https://github.com/smarobix/smarobix-buildx-images/releases)

ROS 2 for ARM boards the official buildfarm does not cover. This repository publishes the Docker images that `colcon buildx` cross-builds workspaces in, ROS 2 install trees as `.deb` and `.tar.gz` for boards with no ROS 2 binaries upstream (Pynq, Raspberry Pi OS and Debian), and the Yocto / meta-ros configuration for the Kria K26 and the Raspberry Pi 5 together with the images built from it.

smarobix-buildx-images and smarobix-colcon-buildx are two halves of one toolchain. The images repository defines every supported target — board, OS, architecture and ROS 2 distro — and publishes the Docker images and ROS 2 `.deb` packages for them. smarobix-colcon-buildx is the colcon verb that cross-builds your own workspace inside one of those images. To put ROS 2 on a board, use the images repository; to build your code for that board, use colcon-buildx.

## Get started

Choose board, OS, architecture and ROS 2 distro in the [target picker](https://smarobix.github.io/smarobix-buildx-images/) and it prints the exact commands. There are two separate jobs.

**Put ROS 2 on the board.** On a 64-bit Raspberry Pi OS 13 (trixie) board, for Jazzy:

```bash
wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v1.1.0/smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
sudo apt install ./smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

Install with `apt install ./<file>.deb`; `dpkg -i` skips every declared dependency. A Kria K26 on Ubuntu takes the official packages from packages.ros.org instead, and a Yocto board already has ROS 2 in its image. Tutorial: [Put ROS 2 on a board from a .deb](docs/tutorials/ros-on-a-board.md).

**Cross-build your workspace.** For a K26 running Ubuntu 24.04, write `.buildx.conf` in the workspace root, the directory that holds `src/`:

```ini
method = docker
docker_image = ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy
docker_platform = linux/arm64
```

then install [smarobix-colcon-buildx](https://github.com/smarobix/smarobix-colcon-buildx) and build:

```bash
pip install "git+https://github.com/smarobix/smarobix-colcon-buildx"
colcon buildx
```

The result lands in `cross_install/`, ready to copy to the board. Tutorial: [Cross-build your first workspace for a Kria K26](docs/tutorials/first-cross-build.md).

## What is published

Images are tags of `ghcr.io/smarobix/smarobix-buildx-images`; packages are attached to the `v*` [releases](https://github.com/smarobix/smarobix-buildx-images/releases).

| Family | Boards | Image tags | ROS 2 on the board |
|---|---|---|---|
| Ubuntu | Kria K26 (KV260, KR260) | `k26-jazzy`, `k26-humble` | official packages from packages.ros.org |
| PYNQ | Pynq-Z1, Pynq-Z2 on PYNQ v3.1.1 | `pynq-v3.1.1-jazzy`, `pynq-v3.1.1-humble` | `.deb`, `armhf` |
| Debian | Raspberry Pi and other Debian 12 / 13 boards, 64- and 32-bit | `rpi-arm64-*` and `rpi-armv7-*`, for bookworm and trixie, Humble and Jazzy | `.deb`, `arm64` or `armhf` |
| Yocto, native | Kria K26, Raspberry Pi 5 | `k26-yocto-jazzy`, `rpi5-yocto-jazzy` | built into the board image from `yocto/` |
| Yocto, cross | Kria K26, Raspberry Pi 5 | `k26-oesdk-jazzy`, `rpi5-oesdk-jazzy` | the same |

Every tag with its platform, `.deb` name and hardware status: [docs/reference/targets.md](docs/reference/targets.md).

## Documentation

The site is [smarobix.github.io/smarobix-buildx-images](https://smarobix.github.io/smarobix-buildx-images/), and it carries the colcon-buildx documentation under [`tool/`](https://smarobix.github.io/smarobix-buildx-images/tool/).

- Tutorials — [first cross-build](docs/tutorials/first-cross-build.md) · [ROS 2 on a board](docs/tutorials/ros-on-a-board.md) · [colcon-buildx on meta-ros](docs/tutorials/meta-ros.md)
- How-to — [pick a target](docs/how-to/pick-a-target.md) · [build on an x86_64 host](docs/how-to/build-on-x86_64.md) · [build on the board](docs/how-to/build-on-the-board.md)
- Reference — [targets](docs/reference/targets.md) · [.deb packages](docs/reference/deb-packages.md) · [tested hardware](docs/reference/tested-hardware.md)
- Explanation — [why this exists](docs/explanation/why-this-exists.md) · [Ubuntu or Yocto](docs/explanation/ubuntu-vs-yocto.md) · [native or cross](docs/explanation/native-vs-cross.md) · [why Cyclone DDS](docs/explanation/rmw.md)
- Maintainers — [docs/maintain/](docs/maintain/index.md)

## Contributing

Issues and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers how to work on this repository, and [docs/maintain/](docs/maintain/index.md) covers adding a board, the CI workflows and cutting a release.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2025-2026 SMAROBIX GmbH.

The Yocto configuration under `yocto/` (kas files and the meta-smrbx layer) is MIT-licensed, following the OpenEmbedded convention. The published Docker images and `.deb` packages contain third-party software (the Ubuntu or Debian base, ROS 2, OpenCV and others) that is distributed under its own licences.
