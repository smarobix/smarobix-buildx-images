# smarobix-buildx-images

[![Build images](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml/badge.svg)](https://github.com/smarobix/smarobix-buildx-images/actions/workflows/build-images.yml)
[![Latest release](https://img.shields.io/github/v/release/smarobix/smarobix-buildx-images?include_prereleases&sort=semver&filter=v*)](https://github.com/smarobix/smarobix-buildx-images/releases)

ROS 2 for ARM boards the official buildfarm does not cover: the Docker images that `colcon buildx` cross-builds workspaces in, ROS 2 install trees as `.deb` packages for 32-bit boards with no ROS 2 binaries upstream (Raspberry Pi OS, Debian, PYNQ), and the Yocto / meta-ros configuration for the Kria K26 with the images built from it.

This repository and [smarobix-colcon-buildx](https://github.com/smarobix/smarobix-colcon-buildx), the colcon verb that builds your workspace in these images, share one documentation site:

**<https://smarobix.github.io/smarobix-buildx-images/>**

Start with [Set up your computer](https://smarobix.github.io/smarobix-buildx-images/start/setup/) and follow the four steps. The pages under [`docs/`](docs/) are the site's source; `{{ version }}` in them is filled in with the newest release when the site is built.

## What is published

Images are tags of `ghcr.io/smarobix/smarobix-buildx-images`, one per board, OS and ROS 2 distro: Raspberry Pi and other Debian boards in 32-bit, the Pynq-Z1 and Z2 on PYNQ, and the Kria K26 on Ubuntu and on a Yocto image. Other 64-bit boards on Ubuntu or Debian are left to pixi and RoboStack. Packages are attached to the `v*` [releases](https://github.com/smarobix/smarobix-buildx-images/releases). Every tag with its platform, package and hardware status is in the [targets reference](docs/reference/targets.md), generated from [`targets.yml`](targets.yml).

## Contributing

Issues and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers the mechanics, and [Maintaining](docs/maintain/index.md) covers adding a target, what CI builds and cutting a release.

## License

Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Copyright 2025-2026 SMAROBIX GmbH.

The Yocto configuration under `yocto/` (kas files and the meta-smrbx layer) is MIT-licensed, following the OpenEmbedded convention. The published Docker images and `.deb` packages contain third-party software (the Ubuntu or Debian base, ROS 2, OpenCV and others) that is distributed under its own licences.
