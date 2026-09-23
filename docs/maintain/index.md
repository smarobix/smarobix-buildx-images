# Maintaining

For people who change smarobix-buildx-images. To use the images, start at the [home page](../index.md). The reason behind every unusual line lives in a comment next to it, in the Dockerfiles, `patch-sources`, `ros-build`, `compute-depends.sh`, the kas files and the dev-container recipe. This page is the map.

## Where things live

| Path | What it is |
|---|---|
| `targets.yml` | One entry per published image tag. The single source of truth for targets. |
| `tools/targets.py` | Validates `targets.yml` and generates the CI matrices and the targets reference. `check-docs` fails on a page that names a tag or package the file does not define. |
| `dockerfiles/<family>/` | One directory per Dockerfile family: `k26`, `pynq-z1`, `rpi`, `oesdk`. |
| `.github/workflows/build-images.yml` | Builds and pushes the images. On a `v*` tag it packages the `.deb` files and creates the release. |
| `.github/scripts/compute-depends.sh` | Derives a `.deb`'s `Depends` from the built tree. |
| `yocto/` | kas files and the `meta-smrbx` layer for the Yocto boards. |
| `docs/`, `mkdocs.yml`, `tools/build-site.sh` | This site. colcon-buildx's `docs/` is copied in under `tool/` at build time. |

## One fact, one owner

Board names, image tags, `.deb` names and the tested status come from `targets.yml`, and nothing else types them out. After any change to it:

```bash
python3 tools/targets.py docs -o docs/reference/targets.md
python3 tools/targets.py check-docs docs README.md CONTRIBUTING.md
python3 tools/test_targets.py
```

CI runs the same three. A page that needs a list of targets links to the reference rather than copying it.

## Add a target

1. **Find out whether the buildfarm has binaries** for the board's OS release and architecture ([how](../how-it-works.md#why-these-boards-need-help)). Yes, on Ubuntu: family `ubuntu-apt`, no `.deb`, start from `dockerfiles/k26/`. No: the target builds ROS 2 from source and must ship a `.deb`; start from `dockerfiles/rpi/` for stock Debian (the `SUITE` and `PY_VER` build arguments select the release) or `dockerfiles/pynq-z1/` for a vendor image. A Yocto board is a machine under `yocto/kas/` instead ([Rebuild the Yocto images](yocto.md)).
2. **Match the base image to the board's userspace**, not only to its architecture: libc, libpython, libstdc++ and OpenCV must agree, or the `.deb` installs cleanly and fails at the first `ros2` call. Pin the base by digest (`docker buildx imagetools inspect debian:trixie-slim` prints it) and add the directory to `.github/dependabot.yml`, so the pin gets bumped.
3. **Add the entry to `targets.yml`**, copying a neighbour of the same family; the header comment documents every key. Name the image after what changes the ABI, the downstream release (`pynq-v3.1.1`) or the ISA baseline and suite (`rpi-armv7-trixie`), never after a board model. Leave `tested` empty until the target has run on hardware.
4. **Regenerate and check** as above, then build the image locally before opening the pull request: `docker buildx build --platform <platform> -f dockerfiles/<dir>/Dockerfile.<distro> dockerfiles/<dir>`. A cold source build under emulation takes hours; `--build-arg ROS_BUILD_WORKERS=4` caps the parallelism when builds share a machine.

A new downstream release, a PYNQ or Debian version, is a new target next to the old one: boards in the field do not all update at once. Never change an existing Dockerfile so that the old entries stop producing the old tree; add a stage or a second file. Dropping a version removes its entries and nothing else: the GHCR tag and the release assets stay, and the release notes say so.

## What CI builds

| Event | Builds | Pushes to GHCR | `.deb` and release |
|---|---|---|---|
| Pull request | only the images whose inputs changed | no | no |
| Push to `main` | all | yes, as rolling `:<id>` tags | no |
| `v*` tag | all | yes | yes |

An image's inputs are its `dockerfiles/<dir>/`; `targets.yml`, `tools/targets.py` and the workflow count for all of them. Two things a pull request does not tell you: the `package` job never runs, so `compute-depends.sh`, the control fields and the install message are exercised for the first time on a release; and pull requests do not write the registry cache, so after a base image moves every pull request rebuilds cold until one push to `main` repairs it. A file a Dockerfile `COPY`s, `patch-sources` and `ros-build` among them, rebuilds ROS 2 from source in every image of that family when it changes, even by a comment; batch such changes.

`arm64` images build on the native arm64 runner, because emulated arm64 silently loses files from the merge-install prefix in large builds; `armv7` images build under QEMU on the x86_64 runners, which is unaffected. After a build that matters, check what was published rather than the job result: `docker buildx imagetools inspect <image> --format '{{json .Image}}'` shows the `revision` label.

## Check a `.deb` before a release

`Depends` is computed by `compute-depends.sh` from the ELF objects in the tree; the hand-kept fields in `targets.yml` cover what ELF inspection cannot see, Python imports above all. Run the computation against a published image and compare with the last release's package (`dpkg-deb -I`):

```bash
docker run --rm --platform linux/arm64 -e DISTRO=jazzy \
  -v "$PWD/.github/scripts/compute-depends.sh:/compute-depends.sh:ro" \
  ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy bash /compute-depends.sh
```

Then install the package in a clean `debian:<suite>-slim` container, never in the build image, run a talker and a listener, and repeat with `--no-install-recommends`. What the computation misses is a library no package owns: the Pynq images build OpenCV into `/opt/install`, which the package neither ships nor declares.

## Cut a release

```bash
git switch main && git pull
git tag -a v1.2.0 -m "v1.2.0" && git push origin v1.2.0
```

The tag becomes the package version verbatim, minus the `v`. Use a plain `vMAJOR.MINOR.PATCH`: dpkg reads a `-rc.1` suffix as a Debian revision that sorts *above* the final release. The workflow builds every image, cuts one `.deb` per target with a `deb` entry and attaches them all to one release. If a `package` job fails, rerun it with `gh run rerun <id> --failed` rather than re-tagging. The site takes its download links from the newest `v*` release, so check them afterwards.

Yocto SDK installers are bitbake output, published as assets of their own `yocto-sdk-<distro>-<date>` release and pinned by checksum in `targets.yml`. Create those with `gh release create --latest=false`: they share the release stream, and an SDK release marked as latest breaks every `releases/latest` link. Never name one `v…`, and never replace the assets of an existing one. A new SDK is a new release and new `sdk` values in `targets.yml`.
