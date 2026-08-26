# Contributing

The mechanics of adding a new board (creating a Dockerfile, registering it in the workflow matrix, opening a PR) are covered in [Adding a new board](README.md#adding-a-new-board) in the README. This file covers the parts that need a deliberate decision.

## Does my board have ROS binaries?

Ask this before anything else, and ask it about the **architecture and the distribution together**. REP-2000 tiers describe architectures, but the buildfarm publishes per (distribution, architecture) pair, so a Tier-1 architecture on the wrong distribution has no binaries at all.

Check directly rather than assuming:

```bash
# substitute your board's codename and dpkg architecture
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/<codename>/main/binary-<arch>/Packages.gz \
  | gunzip | grep -c '^Package: ros-<distro>-'
```

Ubuntu Noble on `arm64` returns thousands. Debian `bookworm` and `trixie` return **zero** on every architecture — those dists carry only bootstrap tooling (`ros-dev-tools`, `python3-vcstool`, `rosdep`). That is why the Raspberry Pi targets build from source on `arm64`, even though `arm64` is Tier 1, while the Kria K26 (also `arm64`, but Ubuntu) simply apt-installs.

A nonzero count means you can copy the K26 path. Zero means you build from source, and you also need to ship a `.deb`, because nothing else will put ROS on the board.

## Choosing a Docker base image

The Docker base image must match the runtime environment the artifact will be deployed against — not just architecturally, but at the userspace ABI level (libc, libpython, OpenCV, GStreamer).

**apt-installable targets** (`arm64` on K26, etc.). The runtime is plain Ubuntu shipped by Canonical. `FROM ubuntu:noble` (or `:jammy`) is fine — the ROS buildfarm targets the same Ubuntu releases, so apt packages match the board out of the box. No version of the *base image* needs to be encoded in the published image tag.

**Source-built targets** (`armhf` on Pynq, both architectures on Raspberry Pi). The runtime is a curated downstream image (PYNQ, BalenaOS, Raspberry Pi OS) with its own kernel, custom userspace libraries, and possibly vendor-specific PPAs. The Docker base image must match the Ubuntu/Debian release the curated image is based on, so the binaries link against the same library versions.

For Pynq-Z1/Z2 today: the target is **PYNQ v3.1.1**, which is based on Ubuntu 22.04. The Docker base image is `arm32v7/ubuntu:jammy` for both Jazzy and Humble.

For the Raspberry Pi / Debian boards: Raspberry Pi OS 12 is bookworm and 13 is trixie, so the base is `debian:bookworm-slim` or `debian:trixie-slim`, chosen by a `SUITE` build arg. `PY_VER` must be set to match (`3.11` and `3.13` respectively) — it is what the install tree's `PYTHONPATH` is built around, and a mismatch produces an image that builds cleanly and then fails to import `rclpy` on the board. The architecture is *not* a base-image choice: `debian:*-slim` is a multi-arch manifest, so `buildx --platform` selects it and one Dockerfile covers both.

### Verify the release, don't assume it

Confirm what the board actually runs before choosing a base — a downloaded `.img` is not necessarily the release on the SD card already in the board:

```bash
cat /etc/os-release && dpkg --print-architecture
```

Mixing these up is the most likely way to ship a broken `.deb`: bookworm and trixie differ in `libpython` (3.11 vs 3.13), `libstdc++`, and OpenCV soname (`libopencv-core406` vs `410`), so an install tree built against one will not run on the other.

### Modern toolchains against older ROS source

Newer Debian releases ship compilers that ROS 2 Humble and Jazzy predate. Debian trixie's GCC 14 no longer supplies some headers transitively, so source that relied on that stops compiling — `rmw/time.h` uses `bool` in C while including only `<stdint.h>`, and fails with `unknown type name 'bool'`.

`dockerfiles/rpi/patch-sources` fixes these per file, from a list of `<path>:<header>` entries, and is a no-op for files that are absent or already correct. Add an entry there when a new release breaks another transitive include.

Resist the tempting shortcut of force-including the header globally via `CMAKE_C_FLAGS=-include stdbool.h`. It works for `rmw` and then breaks cyclonedds: `<stdbool.h>` defines `true` and `false` as macros, and the mcpp-derived preprocessor cyclonedds bundles uses `true:` and `false:` as goto labels, so every C translation unit in the tree becomes a hazard. Targeted patches keep the blast radius to the file that actually needs fixing.

## Encoding the target version in the image tag

When the Docker base image is chosen to match a specific downstream release (either source-built case above), encode the downstream's version in the published image tag and `.deb` package name:

| | apt-installable (K26) | Vendor image (Pynq) | Stock Debian (Raspberry Pi) |
|---|---|---|---|
| Matrix `image:` field | `k26` | `pynq-v3.1.1` | `rpi-arm64-trixie` |
| Matrix `pkg:` field | (none) | `pynq-v3.1.1` | `rpi-trixie` |
| GHCR tag | `k26-jazzy` | `pynq-v3.1.1-jazzy` | `rpi-arm64-trixie-jazzy` |
| `.deb` package name | (no `.deb` shipped) | `smarobix-ros-jazzy-pynq-v3.1.1` | `smarobix-ros-jazzy-rpi-trixie` |

The Debian boards vary along two axes at once (OS release and architecture), and both change the ABI, so both must appear in the image tag. The architecture is folded into the `image:` field rather than added as a fourth tag component, which keeps the tag template at `<image>-<distro>` for every board.

**Name the image after the ISA baseline, not a board model.** `rpi-armv7-trixie` is accurate — that image runs on any ARMv7 Debian trixie board. An earlier name, `rpi5-trixie-armhf`, implied a Pi-5-only artifact and was wrong in both directions: it excluded the Pi 2/3/4 and Zero 2 W that the tree supports, and it hid the one board family it genuinely does *not* support, the ARMv6 Pi 1 and Zero. Nothing in these images is Pi-specific in any case; the base is stock Debian.

The `.deb` package name uses a separate `pkg:` field that omits the architecture, because dpkg already carries it in the filename and the `Architecture:` control field. So one package name, `smarobix-ros-jazzy-rpi-trixie`, ships as both `_arm64.deb` and `_armhf.deb` — which is what lets apt pick the right one.

The `image:` field in `.github/workflows/build-images.yml` is decoupled from the `board_dir:` field (which is just where the Dockerfile lives) so the published name can carry meaning the directory name can't.

## How `.deb` dependencies are determined

Do not hand-write the `Depends:` field. It is derived at package time by `.github/scripts/compute-depends.sh`, which runs *inside* the built image and works out what the tree actually links against:

1. Find every ELF object under `/opt/ros/<distro>` — **recursively**, because Python extension modules live under `site-packages/<pkg>/` and pull in libraries nothing else does (`cv_bridge`'s boost extension needs `libboost_python`, which a top-level scan misses).
2. Read each object's `DT_NEEDED` entries. This is deliberately not `ldd`: `ldd` reports the transitive closure, which through OpenCV drags in GDAL, HDF5, Poppler and ~130 packages. A Debian package declares only its own direct links and lets apt resolve the rest.
3. Drop sonames the tree itself provides, resolve the rest via `ldconfig`, canonicalise with `realpath` (`ldd` says `/lib/...` but on a usrmerge system dpkg only knows `/usr/lib/...`), and map to owning packages with `dpkg -S`.

The result was cross-checked against `dpkg-shlibdeps` and matches it exactly. `dpkg-shlibdeps` itself is not used because ROS's `$ORIGIN` RPATHs and unversioned sonames make it fail on this tree.

The reason this is automated: a hand-written list of `libc6, libpython3.x, libstdc++6` — which is what this repo used to carry — omits *sixteen* libraries the tree really loads, including `libopencv-imgcodecs`, `libboost-python`, `libssl`, `libsqlite3`, `libtinyxml2`, `libyaml` and `libzstd`. On a Lite board image none of those are installed, so the package installs cleanly and then fails at first use.

### What automation cannot see, and how it is tiered

ELF inspection says nothing about Python imports, so the matrix carries three hand-kept fields. The lists were produced by parsing every `import` statement in the install tree, keeping the names unresolved on a clean board image, and then confirming by installing the `.deb` in a stock `debian:<suite>-slim` container and running `ros2 topic echo` against a talker.

| Field | Contents | Rationale |
|---|---|---|
| `depends_extra` | `python3`, `argcomplete`, `lark`, `numpy`, `packaging`, `psutil`, `yaml` | Without any one of these `ros2` does not start — `argcomplete` and `packaging` break the CLI outright, `psutil` breaks the daemon, `lark` breaks `ros2 launch` |
| `recommends` | `catkin-pkg`, `cryptography`, `lxml`, `opencv`, `rosdistro` | Optional features. `python3-opencv` only affects `cv_bridge`'s Python bindings (the C++ library links Debian's OpenCV directly and is a hard dependency); `cryptography` is `sros2`; `rosdistro` is `ros2doctor`. `apt install ./file.deb` pulls these in by default, and the tree still works if they are removed |
| `suggests` | `build-essential`, `cmake`, `git`, `python3-dev`, `python3-pip` | Only needed to compile ROS packages *on* the board |

Prefer `Recommends` over `Depends` for anything the tree can run without. `apt install ./file.deb` installs recommendations by default, so users get the full experience anyway, while people building minimal images keep the ability to opt out with `--no-install-recommends`.

Two deliberate exclusions:

- **Test and lint imports** (`pytest`, `flake8`, `mypy`, `pycodestyle`, `pydocstyle`) come from `ament_*` packages and are not needed to run nodes.
- **`empy`** is only used to *generate* interfaces, and Debian ships empy 4.x, whose API `rosidl` does not support. Depending on `python3-empy` would therefore install a version that actively breaks on-board builds. The `postinst` tells users to `pip install 'empy==3.3.4'` instead.

The package also ships a `postinst` that prints the recommended `RMW_IMPLEMENTATION` for the architecture and the on-board build instructions, since `Suggests` are invisible during a normal install.

Verify a change to any of these lists the same way — install the `.deb` in a clean container for the target suite. Do not test in the build image: it has every build dependency already present and will hide a missing runtime dependency.

## Choosing the RMW

Both Fast DDS and Cyclone DDS are built into every tree, and nothing sets `RMW_IMPLEMENTATION`, so the upstream default (Fast DDS) applies unless the user overrides it.

The matrix carries an `rmw` field per entry that feeds the `postinst` recommendation. **Cyclone DDS is recommended wherever memory is tight** — it has a materially smaller footprint, which is the reason the Pynq boards use it. That currently means every `armhf` entry (Pynq and the 32-bit Debian builds); the `arm64` entries recommend Fast DDS, which is the better-tested upstream default and unproblematic on a board with gigabytes to spare.

Set `rmw` on new entries by the board's memory budget, not by its architecture as such.

## Adding support for a new downstream version 

When the curated downstream ships a new release (PYNQ v3.2.0, etc.):

1. Verify the existing Dockerfile still builds against the new release. Update the Ubuntu base image if the new release moved (e.g. `jammy` → `noble`).
2. Add a new matrix entry with the new version, e.g. `image: pynq-v3.2.0`. Do not overwrite `pynq-v3.1.1` unless support for the old version is being explicitly dropped — both versions can coexist so users on different SD-card images get the right binaries.
3. Update the [Compatibility](README.md#compatibility) section in the README to reflect the new tested version.
4. Add a matching entry to the `package` job's matrix if the new version should publish `.deb`s. Each entry carries its own `deb_arch`, `depends`, `target`, and `board`, so several versions and architectures publish in parallel without any shared env vars. Keep `depends` in step with the base image — the `libpython` and `libopencv-*` sonames are release-specific.

## CI

PRs run the full build matrix under QEMU but **do not push to GHCR** — the workflow runs with no secrets and a read-only `GITHUB_TOKEN` on PRs. A green PR build means the Dockerfiles still compile.

Pushes to `main` and `develop` publish to GHCR with rolling tags. Cutting a `v*` git tag triggers the `package` job, which runs once per entry in its matrix (extracts `/opt/ros/<distro>` from the freshly built image, packages it as `.tar.gz` + `.deb`), and then a single `release` job that collects every `pkg-*` artifact and attaches them all to one GitHub Release.

Note that the full matrix is now 12 image builds, most of them emulated. A PR that touches only `dockerfiles/rpi/` still rebuilds everything; that is deliberate for now, since cache hits make the untouched boards cheap.

The Docker Hub mirror (`.github/workflows/dockerhub-mirror.yml`) is `workflow_dispatch` only and inert without `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets.
