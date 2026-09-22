# Add a board

Adding a board means three things: a Dockerfile that builds the right environment, an entry in `targets.yml`, and a pull request. The CI matrices, the [targets reference](../reference/targets.md) and the picker all follow from the `targets.yml` entry. Most of the work is deciding which kind of target the board is, and that decision comes first.

## Does the board have ROS binaries for this distro and architecture?

Ask this about the OS release **and** the architecture together. [REP-2000](https://www.ros.org/reps/rep-2000.html) tiers describe architectures, but the ROS buildfarm publishes per (OS release, architecture) pair. A Tier 1 architecture on an OS release the buildfarm doesn't target has no binaries at all. [Why this exists](../explanation/why-this-exists.md) explains the background.

Check directly rather than assuming:

```bash
# Ubuntu 24.04 (noble), arm64, ROS 2 Jazzy: prints several thousand
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/noble/main/binary-arm64/Packages.gz \
  | gunzip | grep -c '^Package: ros-jazzy-'

# Debian 13 (trixie), arm64, ROS 2 Jazzy: prints 0
curl -sSL http://packages.ros.org/ros2/ubuntu/dists/trixie/main/binary-arm64/Packages.gz \
  | gunzip | grep -c '^Package: ros-jazzy-'
```

For your board, replace the codename with `VERSION_CODENAME` from the board's `/etc/os-release`, `arm64` with the output of `dpkg --print-architecture` on the board, and `jazzy` with the ROS distro. A codename that packages.ros.org doesn't carry also prints 0, because curl gets an error page rather than a gzip file. Either way there are no binaries.

Ubuntu `noble` and `jammy` on `arm64` return thousands. Debian `bookworm` and `trixie` return zero on every architecture: those dists carry only bootstrap tooling such as `ros-dev-tools`. Ubuntu `jammy` on `armhf` also returns zero. That is why the Raspberry Pi targets build ROS from source on `arm64`, even though `arm64` is Tier 1, while the Kria K26 on Ubuntu (also `arm64`) simply apt-installs it.

## Pick the kind of target

| ROS binaries? | The board runs | `family` | Start from | Ships a `.deb`? |
|---|---|---|---|---|
| Yes | Ubuntu | `ubuntu-apt` | `dockerfiles/k26/` | No. Users install ROS from packages.ros.org. |
| No | A vendor image based on Ubuntu or Debian, such as PYNQ | `pynq` | `dockerfiles/pynq-z1/` | Yes |
| No | Stock Debian or Raspberry Pi OS, in several releases or architectures | `debian` | `dockerfiles/rpi/` | Yes |
| Not applicable | A Yocto/meta-ros image | `yocto-native` and `oe-sdk` | `yocto/` and `dockerfiles/oesdk/` | No. ROS is part of the board image. |

A zero count means you build ROS from source, and you must also ship a `.deb`, because nothing else will put ROS on the board.

The families are defined in `tools/targets.py`, and the picker and the generated tables group targets by them. If a new board fits none of them, add the family there first.

A Yocto board works differently: you add a machine under `yocto/kas/`, build the board image, SDK and dev container with bitbake, and publish the last two by hand. [Rebuild the Yocto images](yocto.md) covers that; the `targets.yml` side is the same as below.

## Choose the base image

The Docker base image must match the board's userspace ABI, not only its architecture. [Base images and source fixes](base-images.md) explains how to choose one and how to confirm what the board really runs.

## Write the Dockerfile

Copy the Dockerfile of the matching family into `dockerfiles/<dir>/Dockerfile.<distro>`. A source build also needs an `extra.repos.<distro>` file for `vcs import`. Reuse an existing directory when its Dockerfile can cover the new target through build arguments: `dockerfiles/rpi/` covers eight targets with the `SUITE` and `PY_VER` build arguments and the `--platform` flag.

- **Pin the base image by digest**, as the existing Dockerfiles do. `docker buildx imagetools inspect debian:trixie-slim` prints the digest to paste after the tag as `@sha256:…`.
- **Add a new directory to [`.github/dependabot.yml`](https://github.com/smarobix/smarobix-buildx-images/blob/main/.github/dependabot.yml)**, so that Dependabot bumps the pin. A pin that nobody updates is a base that never gets security fixes.
- **Take care with files a Dockerfile `COPY`s**, such as `extra.repos.*`, `patch-sources` and `ros-build`. Any change to them, even a comment, changes the `COPY` checksum. Every image built from that directory then rebuilds ROS from source, which takes hours per image under emulation.

## Name it

Every image tag is `<image>-<distro>`, and the entry's `id` is that tag. The `.deb` is named `smarobix-ros-<distro>-<pkg>`.

| | `ubuntu-apt` (K26) | `pynq` | `debian` |
|---|---|---|---|
| `image` | `k26` | `pynq-v3.1.1` | `rpi-arm64-trixie` |
| `deb.pkg` | none | `pynq-v3.1.1` | `rpi-trixie` |
| Image tag | `k26-jazzy` | `pynq-v3.1.1-jazzy` | `rpi-arm64-trixie-jazzy` |
| `.deb` package | none | `smarobix-ros-jazzy-pynq-v3.1.1` | `smarobix-ros-jazzy-rpi-trixie` |

- **`image` carries everything that changes the ABI.** When the base is chosen to match a downstream release, the release goes into the name: `pynq-v3.1.1`. The Debian boards vary in OS release and architecture at once, and both change the ABI, so both are in the name. The architecture is folded into `image` rather than added as a fourth part, so the tag template stays `<image>-<distro>` for every board.
- **An apt-installable Ubuntu target carries no OS version.** The buildfarm targets the same Ubuntu releases, so the distro already implies the base: `k26-jazzy` is noble, `k26-humble` is jammy.
- **Name the image after the ISA baseline, not a board model.** `rpi-armv7-trixie` runs on any ARMv7 board with Debian trixie. An earlier name, `rpi5-trixie-armhf`, suggested a Pi-5-only artifact and was wrong both ways. It excluded the Pi 2, 3, 4 and Zero 2 W that the tree supports. It also hid the one family the tree does *not* support: the ARMv6 Pi 1, Zero and Zero W. Nothing in these images is Pi-specific anyway; the base is stock Debian.
- **`deb.pkg` leaves out the architecture.** dpkg already carries it in the filename and in the `Architecture:` control field. So one package name, `smarobix-ros-jazzy-rpi-trixie`, ships as both `_arm64.deb` and `_armhf.deb`, and apt picks the right one.
- **The build directory is only where the Dockerfile lives.** It is set separately from `image`, so the published name can carry meaning that a directory name can't.

## Add the entry to `targets.yml`

Copy a neighbouring entry of the same family and change what differs. The header comment in `targets.yml` documents every key. An entry looks roughly like this:

```yaml
- id: rpi-arm64-trixie-jazzy
  image: rpi-arm64-trixie
  distro: jazzy
  family: debian
  board: Raspberry Pi / Debian
  boards: any 64-bit Raspberry Pi (3, 4, 5, Zero 2 W) or other arm64 Debian board
  os: {name: Raspberry Pi OS / Debian, codename: trixie}
  arch: arm64
  platform: linux/arm64
  build:
    dir: rpi
    dockerfile: Dockerfile.jazzy
    runs_on: [self-hosted, ARM64]
    args: {SUITE: trixie, PY_VER: "3.13"}
  deb:
    pkg: rpi-trixie
    target: Raspberry Pi OS 13 / Debian 13 (trixie), arm64
    depends_extra: python3, python3-argcomplete, python3-lark, python3-numpy, python3-packaging, python3-psutil, python3-yaml
    recommends: python3-catkin-pkg, python3-cryptography, python3-lxml, python3-opencv, python3-rosdistro
    suggests: build-essential cmake git python3-dev python3-empy ros-dev-tools
  rmw: rmw_cyclonedds_cpp
  tested: []
```

The fields that need a decision:

- **`arch` and `platform`.** `arch` is the dpkg architecture of the board's userspace (`arm64`, `armhf`). `platform` is the Docker platform the image runs as (`linux/arm64`, `linux/arm/v7`). An `oe-sdk` image runs on the host, so its `platform` is `null`.
- **`build.runs_on`.** `arm64` targets build on the native arm64 runner, `[self-hosted, ARM64]`. `armv7` targets build under QEMU on the x86_64 hosts, `[self-hosted, X64]`. [CI and releases](ci-and-releases.md#runners) explains why.
- **`deb`.** Leave it out when the target ships no `.deb`. Never list shared libraries here: they are computed from the built tree. The three hand-kept fields are explained in [`.deb` dependencies](deb-dependencies.md). Copy them from an entry for the same ROS distro; Humble also needs `python3-netifaces` in `depends_extra`.
- **`rmw`.** Always `rmw_cyclonedds_cpp`. It is recommended on every target, and the `.deb`'s install message prints it. [Choosing an RMW](../explanation/rmw.md) gives the reasons.
- **`tested`.** Leave it empty until the image or `.deb` has run on real hardware. An empty list shows as "built, not run on hardware". When someone has run it, add a `{board, date, note}` record, and a longer write-up to [Tested hardware](../reference/tested-hardware.md) if there is more to say.
- **Hand-pushed images.** The Yocto dev containers are built by bitbake outside CI. Their entries have `build: null` and `published: manual`.

Then regenerate the reference page and check the docs:

```bash
python3 tools/targets.py docs
python3 tools/targets.py check-docs $(git ls-files '*.md')
```

Commit the regenerated `docs/reference/targets.md` with the `targets.yml` change. Nothing else needs editing by hand. The build matrix comes from `python3 tools/targets.py matrix build` and the package matrix from `python3 tools/targets.py matrix package`, and the picker reads the same data when the site is built.

## Build it locally first

A pull request build tells you whether the Dockerfile compiles, but a local build is faster to iterate on. On an x86_64 host, register QEMU once (Docker Desktop already includes it):

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Then build the image for the target you added:

```bash
# Kria K26, Jazzy: apt-installs ROS, so it is quick
docker buildx build --platform linux/arm64 --load \
  -f dockerfiles/k26/Dockerfile.jazzy \
  -t buildx-local:k26-jazzy dockerfiles/k26

# Pynq, Jazzy: builds ROS 2 from source under armv7 emulation, so it is slow
docker buildx build --platform linux/arm/v7 --load \
  -f dockerfiles/pynq-z1/Dockerfile.jazzy \
  -t buildx-local:pynq-v3.1.1-jazzy dockerfiles/pynq-z1

# Debian trixie, 64-bit: native on an arm64 host
docker buildx build --platform linux/arm64 --load \
  --build-arg SUITE=trixie --build-arg PY_VER=3.13 \
  -f dockerfiles/rpi/Dockerfile.jazzy \
  -t buildx-local:rpi-arm64-trixie-jazzy dockerfiles/rpi

# Debian bookworm, 32-bit: emulated, slow
docker buildx build --platform linux/arm/v7 --load \
  --build-arg SUITE=bookworm --build-arg PY_VER=3.11 \
  -f dockerfiles/rpi/Dockerfile.jazzy \
  -t buildx-local:rpi-armv7-bookworm-jazzy dockerfiles/rpi
```

`SUITE` and `PY_VER` must agree (`trixie` with `3.13`, `bookworm` with `3.11`). Together they set the base image and the `PYTHONPATH` of the install tree.

The `arm64` builds run natively on Apple Silicon or another `arm64` host and are much faster than the `armv7` ones, which compile ROS 2 under emulation. `dockerfiles/rpi/ros-build` sizes colcon's parallelism from memory, not core count: some ROS translation units need well over a gigabyte in `cc1plus`, so one job per core gets the compiler killed on a machine with less than about 2 GB per core. When several builds share a machine, cap it with `--build-arg ROS_BUILD_WORKERS=4`.

[Build on x86_64](../how-to/build-on-x86_64.md) has more on emulation.

## Open a pull request

Open an issue first if the board needs discussion, then a pull request against `main`. Because the pull request changes `targets.yml`, CI builds every image. The untouched ones are quick when their registry caches are warm. A pull request never pushes anything. [CI and releases](ci-and-releases.md) has the details.

After the merge, the push to `main` publishes `ghcr.io/smarobix/smarobix-buildx-images:<id>`. A `.deb` appears with the next `v*` release. Check what was published, not just the job result. The `org.opencontainers.image.revision` label should be the merge commit:

```bash
docker buildx imagetools inspect ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy \
  --format '{{json .Image}}'
```
