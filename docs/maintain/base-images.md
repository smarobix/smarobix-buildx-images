# Base images and source fixes

A published image is only useful if what it builds runs on the board. That is a question about the userspace ABI, not about the architecture, and it is decided by the Docker base image. This page covers choosing one, confirming what the board really runs, and the fixes that modern toolchains need when they compile older ROS 2 source.

## Match the ABI, not just the architecture

The base image must match the environment the artifact is deployed into at the library level: libc, libpython, libstdc++, OpenCV, GStreamer. Two `arm64` systems are not interchangeable if one is Ubuntu 24.04 and the other Debian 12.

**apt-installable targets** (`ubuntu-apt`, the K26). The runtime is plain Ubuntu from Canonical, and the ROS buildfarm targets the same Ubuntu releases, so apt packages match the board out of the box. `arm64v8/ubuntu:noble` for Jazzy; the Humble image builds on `arm64v8/ros:humble-ros-base`, which is jammy. No base-image version needs to appear in the published tag, because the ROS distro already implies the Ubuntu release.

**Source-built targets on a vendor image** (`pynq`). The runtime is a curated downstream image with its own kernel, its own userspace libraries and sometimes vendor PPAs. The base must match the Ubuntu or Debian release that image is built on. PYNQ v3.1.1 is Ubuntu 22.04, so the base is `arm32v7/ubuntu:jammy` for both Humble and Jazzy.

**Source-built targets on stock Debian** (`debian`). Raspberry Pi OS 12 is bookworm and 13 is trixie, so the base is `debian:bookworm-slim` or `debian:trixie-slim`, selected by the `SUITE` build argument. `PY_VER` must agree (`3.11` and `3.13`): it is what the install tree's `PYTHONPATH` is built around, and a mismatch produces an image that builds cleanly and then fails to import `rclpy` on the board. The architecture is not a base-image choice. `debian:*-slim` is a multi-arch manifest, so `buildx --platform` selects it and one Dockerfile covers both architectures.

**SDK images** (`oe-sdk`). The base is our own dev container for that board, built by bitbake from the same configuration as the board image, so the ABI question is settled by [the Yocto build](yocto.md) rather than by a distro tag.

## Verify the release, don't assume it

A downloaded `.img` is not necessarily the release on the SD card already in the board. Ask the board:

```bash
cat /etc/os-release && dpkg --print-architecture
```

Getting this wrong is the most likely way to ship a broken `.deb`. bookworm and trixie differ in `libpython` (3.11 against 3.13), in `libstdc++`, and in the OpenCV soname (`libopencv-core406` against `libopencv-core410`), so an install tree built against one does not run on the other. The published `Depends` fields show the split plainly: the bookworm packages depend on `libopencv-core406` and `libpython3.11`, the trixie ones on `libopencv-core410` and `libpython3.13`.

## Pinned by digest

Every base is pinned by digest, and Dependabot bumps the pins weekly. An upstream base that moves invalidates every cached layer, and a pull request cannot refresh the registry cache, so a silent bump turns the next unrelated pull request into a multi-hour source rebuild. A digest makes the bump deliberate: it arrives as a pull request, which the path filter turns into a build of just that image, and the rebuild lands on `main` with a cache export.

The `rpi` Dockerfiles carry one pinned stage per suite, because a digest cannot be pasted onto `debian:${SUITE}-slim`. `SUITE` selects the stage and BuildKit only pulls the one it needs. `dockerfiles/oesdk` stays on a tag: its base is our own dev container, which moves only when someone rebuilds it with bitbake.

To find the digest for a new pin:

```bash
docker buildx imagetools inspect debian:trixie-slim
```

## Where OpenCV comes from

Each family solves this differently, and the difference matters when you read a `Depends` field.

| Family | OpenCV | Why |
|---|---|---|
| `ubuntu-apt` (K26) | Built from source into `/opt/install`, with contrib modules: 4.10.0 for Jazzy, 4.5.0 for Humble | The vendor runtime needs a specific OpenCV, and these images ship no `.deb`, so nothing has to declare it |
| `pynq` | Built from source into `/opt/install`: 4.13.0 | Same reason, but these images do ship a `.deb`; see below |
| `debian` | Debian's `libopencv-dev` | `cv_bridge` then links the very OpenCV that the board's own apt installs, so the `.deb` can declare a real dependency on it. It also removes the slowest layer of the build. |

An OpenCV under `/opt/install` is not owned by any dpkg package, and the `.deb` ships only `/opt/ros/<distro>`. [`.deb` dependencies](deb-dependencies.md#what-the-computation-cannot-see) describes what that costs on the Pynq packages.

The Jazzy trees import `vision_opencv` from its `rolling` branch (see `extra.repos.jazzy`), so a cold rebuild can pick up a newer `cv_bridge` than the last one did. Pinning it to the `4.1.0` release is a [known follow-up](#known-follow-ups).

## Modern toolchains against older ROS source

Newer Debian releases ship compilers and Python versions that ROS 2 Humble and Jazzy predate. [`dockerfiles/rpi/patch-sources`](https://github.com/smarobix/smarobix-buildx-images/blob/main/dockerfiles/rpi/patch-sources) fixes that source before the build. It runs in the `rpi` images only; the jammy-based Pynq images have an older toolchain and need none of it.

Every fix in it is a no-op when its target is absent or already correct, so one script serves every suite and both ROS distros. The pybind11 and mcap blocks fail the build loudly if they match but do not apply, rather than leaving a half-patched tree.

There are three kinds of fix in it.

### 1. Transitive includes that stopped being transitive

GCC 13 and later no longer supply some headers indirectly, so source that relied on that stops compiling. `rmw/time.h` uses `bool` in C while including only `<stdint.h>`, and fails with `unknown type name 'bool'`.

The fix is a list of `<path-relative-to-src>:<header>` entries. The header is inserted after the file's first `#include`, so it lands inside any include guard rather than ahead of it. Add an entry when a new release breaks another one.

**Do not force the header in globally** with something like `CMAKE_C_FLAGS=-include stdbool.h`. It fixes `rmw` and then breaks cyclonedds: `<stdbool.h>` defines `true` and `false` as macros, and the mcpp-derived preprocessor that cyclonedds bundles uses `true:` and `false:` as goto labels in `src/tools/idlpp/src/system.c`. It then fails with `expected identifier before numeric constant`. A global flag makes every C translation unit in the tree a hazard; a per-file patch keeps the blast radius to the file that needs it.

### 2. A vendored dependency that is too old for the new Python

Humble's `pybind11_vendor` pins pybind11 v2.9.1, which predates Python 3.11 making `PyFrameObject` an opaque type. `rclpy` then fails with `invalid use of incomplete type 'PyFrameObject'` on bookworm (3.11) as well as trixie (3.13). pybind11 gained 3.11 support in 2.10 and 3.13 support in 2.13, so the script moves the pin to v2.13.6, which covers every suite we target.

The same vendor package applies a Windows-only `Py_DEBUG` patch unconditionally, not guarded by `if(WIN32)`. It is written against the 2.9.1 tree, so `git apply` fails against 2.13.6 and takes the build with it. The script removes that `PATCH_COMMAND` too. Jazzy's `pybind11_vendor` has a different structure (v2.11.1) and builds fine on 3.13, so the block does not match it.

### 3. Upstream `-Werror` against a warning the compiler only emits here

Humble's `mcap_vendor` builds the vendored mcap library with `-Wall -Wextra -Wpedantic -Werror`. bookworm's GCC 12 emits a false `-Wmaybe-uninitialized` on mcap's `intervaltree.hpp`, and `-Werror` turns it into a build failure. trixie's GCC 14 does not warn there, so this one bites bookworm only, which is the opposite direction to the pybind11 fix: there the newer Python was the problem, here it is the older compiler.

The script drops `-Werror` from that line, which is what upstream already did in Jazzy, so Humble ends up matching what Jazzy ships. Warnings are still printed; they just stop failing the build.

### Changing patch-sources

`patch-sources` is `COPY`'d into the image, so any edit changes the layer's checksum and rebuilds ROS from source in all eight Debian images. Batch such changes, and expect the first build after them to be cold.

## Building ROS from source

`dockerfiles/rpi/ros-build` wraps the colcon invocations:

- **Parallelism is capped by memory, not core count.** One worker per 2 GB, never more than one per core. Some translation units need well over a gigabyte in `cc1plus`, so one job per core gets the compiler killed on a machine with less than about 2 GB per core. `ROS_BUILD_WORKERS` overrides the calculation, which is what to use when several builds share a machine. `MAKEFLAGS=-j1` keeps the worker count the whole story.
- **colcon is retried up to three times.** The merge-install prefix is a shared mutable directory, and `pkg_resources` walks every `sys.path` entry when it is imported, so a tool that pulls it in can observe a package mid-install and die on a half-written `egg-info`. The retry is effective rather than hopeful: `build/` is only removed after a successful colcon run, so a retry resumes with the finished packages intact.
- **The build is split into phases.** Phase 4 is last and is meant to be edited; phases 1 to 3 stay cached when you add a package there. The separate phase that builds `rmw_cyclonedds_cpp` is redundant, because `rclcpp` already pulls in every RMW; removing it is a [known follow-up](#known-follow-ups).

What the trees contain, and what is deliberately left out, is in [`.deb` packages](../reference/deb-packages.md).

## Known follow-ups

Each of these changes a Dockerfile or a file a Dockerfile `COPY`s, so doing it rebuilds ROS from source in every image of that family. They are worth batching into one pull request.

| Change | Why |
|---|---|
| Pin `vision_opencv` to `4.1.0` in `dockerfiles/rpi/extra.repos.jazzy` | It tracks the `rolling` branch today, so two builds of the same commit can produce different trees. |
| Drop the phase that builds `rmw_cyclonedds_cpp` on its own | `rclcpp` already builds every RMW, so the step does nothing. |
| Add the ROS apt source in `dockerfiles/k26/Dockerfile.jazzy` with `ros2-apt-source` | The Dockerfile dearmors the key and writes the sources list by hand. The `ros2-apt-source` package is the method upstream maintains. |
