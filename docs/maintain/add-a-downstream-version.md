# Add a downstream version

Some targets are built against a specific downstream release: a vendor SD-card image such as PYNQ, or a Debian release. When a new one appears, it becomes a new target. The existing one stays.

That is the whole rule. Boards in the field do not all update at once, and an install tree built against one release does not run on the next: the libc, libpython and OpenCV sonames differ. The downstream version is part of the image tag and the `.deb` package name precisely so that both can exist side by side and each user gets the binaries for the card in their board. Dropping an old version is a separate, deliberate decision.

The naming rules are in [Add a board](add-a-board.md#name-it), and the base-image reasoning in [Base images and source fixes](base-images.md).

## A new PYNQ release

1. **Find out what the release is based on.** The [PYNQ releases page](https://github.com/Xilinx/PYNQ/releases) says, and a board that already runs it answers directly with `cat /etc/os-release`. PYNQ v3.1.1 is Ubuntu 22.04, which is why the current base is `arm32v7/ubuntu:jammy`.
2. **Decide what the Dockerfile has to do.**
   - If the base did not move, the new entries can build from the existing Dockerfile unchanged.
   - If it moved, say to Ubuntu 24.04, **do not edit the existing Dockerfile in place**: the v3.1.1 entries still build from it, and they must keep producing a jammy tree. Add a second Dockerfile, or a second directory, for the new base, and point the new entries' `build` at it.
3. **Add new entries to `targets.yml`**, one per ROS distro. Copy the two `pynq-v3.1.1` entries and change the version in `image` and in `deb.pkg`, so that a PYNQ v3.2.0 target gets `image: pynq-v3.2.0` and `deb.pkg: pynq-v3.2.0`. The tags and the package names follow from those two values. Update `deb.target` and `os` to the new release, and `boards` if the release supports different boards. Leave the old entries alone, including their `tested` records.
4. **Regenerate and check the docs**, as after any `targets.yml` change:

   ```bash
   python3 tools/targets.py docs
   python3 tools/targets.py check-docs $(git ls-files '*.md')
   ```

5. **Build it locally**, then open the pull request. Because `targets.yml` changed, CI builds every image.
6. **Verify against the new release, not against the old one.** Install the new `.deb` in a clean container for the new base, and then on a board running the new SD-card image; see [`.deb` dependencies](deb-dependencies.md#check-a-change-before-it-ships). When it has run on hardware, add a `tested` record and, if there is more to say, an entry in [Tested hardware](../reference/tested-hardware.md).

Users on the old release keep their existing package name, and the new one appears with the next `v*` release.

## A new Debian or Raspberry Pi OS release

The same shape, with the suite in place of the vendor version. The `rpi` Dockerfiles carry one pinned base stage per suite, so a new suite is a new stage rather than a changed one.

1. **Work out the suite's Python version**, which `PY_VER` must match:

   ```bash
   docker run --rm debian:forky-slim sh -c 'apt-get update -qq && apt-cache show python3 | grep -m1 ^Version'
   ```

2. **Add a stage to both `rpi` Dockerfiles**, pinned by digest, in the form `FROM debian:forky-slim@sha256:… AS base-forky`. `SUITE` then selects it.
3. **Add four entries per ROS distro pair**: `arm64` and `armv7`, Jazzy and Humble. The `.deb` package name takes the suite, as `rpi-trixie` does today.
4. **Expect new toolchain breakage.** A newer GCC or Python may need another entry in `patch-sources`; see [Modern toolchains against older ROS source](base-images.md#modern-toolchains-against-older-ros-source). Editing that file rebuilds every Debian image from source.
5. Regenerate, check, build locally, open the pull request, verify on hardware, as above.

## Dropping a version

Removing the entries from `targets.yml` stops CI building that target and takes it out of the generated table and the picker. Three things it does not do:

- **It does not delete the GHCR tag.** The tag stays at its last build until someone deletes it in the package settings. Leaving it is reasonable; it is still the right image for anyone on that SD-card release.
- **It does not touch past releases.** The `.deb` and `.tar.gz` files stay attached to the releases that published them, and documented links point at those tags. Don't delete release assets.
- **It does not tell anyone.** Say so in the release notes of the first release that no longer ships the package.
