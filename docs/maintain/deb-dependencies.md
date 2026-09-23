# `.deb` dependencies

A `.deb` here ships one thing, `/opt/ros/<distro>`, and declares everything the board must already have. Most of that declaration is computed from the built tree. Three fields cannot be computed and are kept by hand in `targets.yml`. This page is about both, and about how to check a change before a release makes it public. The user-facing view of the same packages is in [`.deb` packages](../reference/deb-packages.md).

## How `Depends` is computed

Never hand-write a shared-library dependency. [`.github/scripts/compute-depends.sh`](https://github.com/smarobix/smarobix-buildx-images/blob/main/.github/scripts/compute-depends.sh) derives the list at package time. It runs *inside* the built image, where the tree's own libraries resolve and the exact runtime packages it linked against are installed.

1. **Find every ELF object under `/opt/ros/<distro>`, recursively.** Python extension modules live under `site-packages/<pkg>/` and pull in libraries nothing else does: `cv_bridge`'s boost extension needs `libboost_python`, which a top-level scan misses.
2. **Read each object's `DT_NEEDED` entries** with `objdump -p`. This is deliberately not `ldd`. `ldd` reports the transitive closure, which through OpenCV drags in GDAL, HDF5, Poppler and around 130 packages. A Debian package declares only what its own objects link against and lets apt resolve the rest through those packages' own dependencies.
3. **Drop the sonames the tree itself provides**, matched on basename anywhere in the tree, since ROS libraries are not all directly under `lib/`.
4. **Resolve the rest through the linker cache, then canonicalise.** `ldconfig -p` is snapshotted once rather than run per soname: it is hundreds of times fewer processes, and piping `ldconfig -p` into an `awk` that exits on the first match makes `ldconfig` die of `SIGPIPE`, which under `pipefail` surfaces as exit 141 and kills the script. Whether that happens is a timing race, so it passed on trixie and failed on bookworm purely because the caches differ in size. Each path is then passed through `realpath`, because the linker reports `/lib/...` while dpkg may know the same file as `/usr/lib/...`, and because the soname is a symlink to the versioned file the package actually ships.
5. **Map each library to its owning package** with `dpkg -S`, dropping diversion lines and architecture qualifiers such as `:arm64`.

The script fails the job if any stage produces nothing, and the workflow fails if the output is empty. A silent empty `Depends` would ship a package that installs anywhere and works nowhere.

The result was cross-checked against `dpkg-shlibdeps` and matched it. `dpkg-shlibdeps` is not used because ROS's `$ORIGIN` RPATHs and unversioned sonames make it fail on this tree.

The reason for automating this at all: the hand-written list this repository used to carry, `libc6, libpython3.x, libstdc++6`, omitted more than a dozen libraries the tree really loads, among them `libopencv-imgcodecs`, `libboost-python`, `libssl`, `libsqlite3`, `libtinyxml2`, `libyaml`, `libzstd`, `liblz4`, `libacl1` and `liblttng-ust`. On a Lite board image none of those are installed, so the package installed cleanly and then failed at first use.

## What the computation cannot see

**Python imports.** ELF inspection says nothing about `import`. That gap is what the hand-kept fields below cover.

**Libraries that no package owns.** A lookup miss is not fatal, by design, so anything outside dpkg's world is dropped silently. The Pynq images build OpenCV 4.13.0 from source into `/opt/install`, and the `.deb` ships only `/opt/ros/<distro>`. In the v1.1.0 packages, `libcv_bridge.so` therefore needs `libopencv_core.so.413`, `libopencv_imgproc.so.413` and `libopencv_imgcodecs.so.413`, and the package neither ships them nor declares them. `cv_bridge` works in the image and fails on a board that has no matching OpenCV. The Debian images avoid this by using Debian's `libopencv-dev`, which lets the package declare a real dependency.

**Files dpkg records under `/lib`.** Step 4 canonicalises to `/usr/lib/...`, which matches dpkg's file list only where the package has moved there. On trixie the v1.1.0 packages depend on `libc6` and `libgcc-s1`; on bookworm and on jammy (Pynq) those two drop out. Both are essential or required packages that any board already has, so it has not mattered, but a non-essential library in the same position would be missed.

## The hand-kept fields

These live in each `deb` entry in `targets.yml`. The lists were produced by parsing every `import` statement in the install tree, keeping the names that do not resolve on a clean board image, and confirming by installing the `.deb` in a stock container and running a talker and a listener.

| Field | Contents | Why |
|---|---|---|
| `depends_extra` | `python3`, `python3-argcomplete`, `python3-lark`, `python3-numpy`, `python3-packaging`, `python3-psutil`, `python3-yaml` | Without any one of these `ros2` does not start: `argcomplete` and `packaging` break the CLI outright, `psutil` breaks the daemon, `lark` breaks `ros2 launch`. Humble also needs `python3-netifaces`. |
| `recommends` | `python3-catkin-pkg`, `python3-cryptography`, `python3-lxml`, `python3-opencv`, `python3-rosdistro` | Optional features. `python3-opencv` affects only `cv_bridge`'s Python bindings, since the C++ library links the system OpenCV directly; `cryptography` is for `sros2`; `rosdistro` is for `ros2doctor`. `apt install ./file.deb` pulls these in by default and the tree runs without them. |
| `suggests` | The toolchain needed to compile ROS packages *on* the board | Not needed to run nodes. The field is space-separated so the install message can paste it straight into an `apt install` command; the comma form for the control field is derived from it. |

Prefer `Recommends` to `Depends` for anything the tree can run without. `apt install ./file.deb` installs recommendations by default, so users get the full experience anyway, while people building minimal images can still opt out with `--no-install-recommends`.

Two deliberate exclusions:

- **Test and lint imports** (`pytest`, `flake8`, `mypy`, `pycodestyle`, `pydocstyle`) come from `ament_*` packages and are not needed to run nodes.
- **empy** is used only to *generate* interface code, which is a build-time job, not a runtime one. It belongs with the on-board build tools, not in `Depends`. Debian bookworm and trixie and Ubuntu jammy all ship `python3-empy` 3.3.4, which rosidl supports, so installing it on the board is a plain `apt install`. The version rosidl cannot use is in Debian experimental only, and no released suite offers it.

The control file is assembled as `Depends: <computed>, <depends_extra>`, followed by `Recommends` and `Suggests` straight from the entry, and a `Description` built from the entry's `target` and `boards` text.

## The install message

The package ships a `postinst` that prints, on configure:

- where the tree was installed and how to source it;
- the recommended `RMW_IMPLEMENTATION`, which is `rmw_cyclonedds_cpp` on every target (see [Choosing an RMW](../explanation/rmw.md));
- how to add the tools for building ROS packages on the board, as in [Build on the board](../how-to/build-on-the-board.md).

It exists because neither channel reaches the user otherwise: `Suggests` are invisible during a normal install, and nothing in the tree sets `RMW_IMPLEMENTATION`, so the user has to export it.

## Check a change before it ships

The `package` job runs only on a `v*` tag, so **a pull request does not exercise any of this**. A change to `compute-depends.sh`, to the control fields or to the install message reaches CI for the first time during a release. Check it by hand first.

**Run the computation against a published image.** This is the same command the workflow runs:

```bash
docker run --rm --platform linux/arm64 -e DISTRO=jazzy \
  -v "$PWD/.github/scripts/compute-depends.sh:/compute-depends.sh:ro" \
  ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy \
  bash /compute-depends.sh
```

Compare the output with the `Depends` field of the last release's package for the same target. `dpkg-deb -I <file>.deb` prints it.

**Assemble a package locally** when you changed a control field or the install message. These are the package job's steps, minus the upload; run them on a Linux host or inside a container, because they need `dpkg-deb`:

```bash
IMAGE=ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy
CID=$(docker create --platform linux/arm64 "$IMAGE")
mkdir -p stage/DEBIAN stage/opt/ros
docker cp "$CID:/opt/ros/jazzy" stage/opt/ros/jazzy
docker rm "$CID"
# write stage/DEBIAN/control and stage/DEBIAN/postinst as the workflow does,
# with the Depends printed by the previous command
chmod 0755 stage/DEBIAN/postinst
dpkg-deb --root-owner-group --build stage test.deb
```

**Install it in a clean container for the target suite**, never in the build image. The build image has every build dependency already present and will hide a missing runtime dependency:

```bash
docker run --rm -it --platform linux/arm64 -v "$PWD:/pkg:ro" debian:trixie-slim bash
```

Inside the container:

```bash
apt-get update
apt-get install -y /pkg/smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
source /opt/ros/jazzy/setup.bash
ros2 run demo_nodes_cpp talker &
ros2 topic echo /chatter --once
```

Repeat with `--no-install-recommends` to confirm that everything in `Recommends` really is optional. Use `debian:bookworm-slim` for a bookworm package, and a PYNQ-matching `arm32v7/ubuntu:jammy` for a Pynq one. On an x86_64 host, register QEMU first; see [Build on x86_64](../how-to/build-on-x86_64.md).

A released package is easy to get hold of for comparison:

```bash
curl -fsSLO https://github.com/smarobix/smarobix-buildx-images/releases/download/v1.1.0/smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb
```
