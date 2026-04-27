# Contributing

The mechanics of adding a new board (creating a Dockerfile, registering it in the workflow matrix, opening a PR) are covered in [Adding a new board](README.md#adding-a-new-board) in the README. This file covers the parts that need a deliberate decision.

## Choosing a Docker base image

The Docker base image must match the runtime environment the artifact will be deployed against — not just architecturally, but at the userspace ABI level (libc, libpython, OpenCV, GStreamer).

**Tier-1 architectures** (`arm64` on K26, etc.). The runtime is plain Ubuntu shipped by Canonical. `FROM ubuntu:noble` (or `:jammy`) is fine — the ROS buildfarm targets the same Ubuntu releases, so apt packages match the board out of the box. No version of the *base image* needs to be encoded in the published image tag.

**Tier-3 architectures** (`armhf` on Pynq, etc.). The runtime is usually a curated downstream image (PYNQ, BalenaOS, Raspberry Pi OS) with its own kernel, custom userspace libraries, and possibly Xilinx- or vendor-specific PPAs. The Docker base image must match the Ubuntu/Debian release the curated image is based on, so the binaries link against the same library versions.

For Pynq-Z1/Z2 today: the target is **PYNQ v3.1.1**, which is based on Ubuntu 22.04. The Docker base image is `arm32v7/ubuntu:jammy` for both Jazzy and Humble.

## Encoding the target version in the image tag

When the Docker base image is chosen to match a curated downstream (the Tier-3 case above), encode the downstream's version in the published image tag and `.deb` package name:

| | Tier-1 (K26) | Tier-3 (Pynq) |
|---|---|---|
| Matrix `image:` field | `k26` | `pynq-v3.1.1` |
| GHCR tag | `k26-jazzy` | `pynq-v3.1.1-jazzy` |
| `.deb` package name | (no `.deb` shipped) | `smarobix-ros-jazzy-pynq-v3.1.1` |

The `image:` field in `.github/workflows/build-images.yml` is decoupled from the `board_dir:` field (which is just where the Dockerfile lives) so the published name can carry meaning the directory name can't.

## Adding support for a new downstream version 

When the curated downstream ships a new release (PYNQ v3.2.0, etc.):

1. Verify the existing Dockerfile still builds against the new release. Update the Ubuntu base image if the new release moved (e.g. `jammy` → `noble`).
2. Add a new matrix entry with the new version, e.g. `image: pynq-v3.2.0`. Do not overwrite `pynq-v3.1.1` unless support for the old version is being explicitly dropped — both versions can coexist so users on different SD-card images get the right binaries.
3. Update the [Compatibility](README.md#compatibility) section in the README to reflect the new tested version.
4. Bump the `PYNQ_IMAGE` and `PYNQ_TARGET` env vars on the `package-pynq` job if you intend new releases to publish `.deb`s for the new version. (If you're publishing `.deb`s for multiple PYNQ versions in parallel, that's a larger refactor — open an issue first.)

## CI

PRs run the full build matrix under QEMU but **do not push to GHCR** — the workflow runs with no secrets and a read-only `GITHUB_TOKEN` on PRs. A green PR build means the Dockerfiles still compile.

Pushes to `main` and `develop` publish to GHCR with rolling tags. Cutting a `v*` git tag triggers the `.deb` release job (extracts `/opt/ros/<distro>` from the freshly built Pynq image, packages it as `.tar.gz` + `.deb`, attaches both to a GitHub Release).

The Docker Hub mirror (`.github/workflows/dockerhub-mirror.yml`) is `workflow_dispatch` only and inert without `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets.
