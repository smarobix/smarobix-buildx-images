# Why this exists

ROS 2 is distributed as binary apt packages, but only for a few operating systems. Most
small ARM boards do not run one of them. This repository fills that gap in two ways: it
builds ROS 2 once for the boards that have no binaries and ships the result, and it
publishes the images that `colcon buildx` builds your own workspace in.

## Tiers describe architectures; binaries exist per distribution *and* architecture

[REP-2000](https://www.ros.org/reps/rep-2000.html) assigns a support tier to each
platform of a ROS 2 release. `armhf` is Tier 3, and the buildfarm publishes no `armhf`
ROS 2 packages for Humble or Jazzy at all.

Tier 1 is not by itself an answer either, because the buildfarm builds for a
*(distribution, architecture)* pair. `arm64` is Tier 1, but Raspberry Pi OS is Debian,
and there are no ROS 2 binaries for any Debian release on any architecture. The Debian
dists on packages.ros.org carry the bootstrap tooling — `ros-dev-tools`, `vcstool`,
`rosdep` — and nothing else.

Count it for your own board rather than assuming:

```bash
# substitute your board's codename, dpkg architecture and ROS distro
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/<codename>/main/binary-<arch>/Packages.gz \
  | gunzip | grep -c '^Package: ros-<distro>-'
```

Ubuntu noble on `arm64` answers with thousands of Jazzy packages, and jammy on `arm64`
with thousands of Humble ones. Debian bookworm and trixie answer zero on every
architecture, and so does jammy on `armhf`.

## What the alternatives cost

Without binaries, a board has two options, and both are bad:

- **Build ROS 2 on the board.** Hours of compiling on a machine with little memory, and
  it has to be repeated when the operating system moves a library out from under the
  tree.
- **Build ROS 2 as part of every workspace.** The same hours, once per workspace and
  once per machine.

So this repository does the source build once per (board, OS, architecture, distro), in
CI, scopes it to a usable subset of `ros-base`, and ships the install tree as a `.deb`
that drops into `/opt/ros/<distro>` with real dependencies on the board's own libraries.
That is the Pynq and the Raspberry Pi OS / Debian case. See
[.deb packages](../reference/deb-packages.md).

## Boards that do have binaries still need an image

A Kria K26 running Ubuntu installs ROS 2 from packages.ros.org like any other Ubuntu
machine. What is missing there is a *build* environment for your workspace that matches
the board: the same Ubuntu release and the same ROS 2 packages, plus a cross toolchain,
GStreamer and the Xilinx PPAs. That is what the `k26-*` images are, and building your
workspace in one keeps the toolchain off your laptop and the result linked against what
the board actually has.

## Boards that run Yocto need neither

On a Yocto / meta-ros board, ROS 2 is part of the board image, built from source by
bitbake along with everything else. Nothing from apt is involved and nothing from here
is installed on the board. What this repository publishes for those boards is the
configuration the images are built from, plus two images to build workspaces against:
see [Ubuntu or Yocto](ubuntu-vs-yocto.md).

## And then the workspace

Putting ROS 2 on a board is only half of the job. The other half is building your own
packages for it, which is what
[smarobix-colcon-buildx](https://github.com/smarobix/smarobix-colcon-buildx) does with
the images published here. The two halves are deliberately kept apart on every page:
they have different answers for the same board, and running them together is what made
the older documentation confusing.
