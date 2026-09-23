# Tested hardware

What has been run, where, and when. CI builds every published target on every release,
which says the image builds; this page records the checks beyond that. A target that is
not listed here has been built but has not been run on a board.

The short per-target note in [Targets](targets.md) comes from the same records.

Most entries use the demo workspace from
[colcon-buildx on meta-ros](../tutorials/meta-ros.md): an interface package `demo_msgs`
and an `rclcpp` publisher `demo_node` that depends on it, which together exercise the
rosidl generators and a package finding another package from the same workspace.

## Kria KV260, Yocto (meta-ros Jazzy, scarthgap)

| Date | What was run | Result |
|---|---|---|
| 2026-09-13 | The board image `ros-image-core` for `k26-smk-kv-sdt`, booted from SD | Boots to a shell; `ros2 pkg list` works and lists 124 packages |
| 2026-09-13 | `colcon buildx --method sdk` with the K26 SDK on an arm64 Linux host, result deployed to the board | 13.4 s cold, 1.6 s no-op, 7.3 s incremental. `talker` runs at 2 Hz, 26 MB RSS; `ros2 topic info /num` sees it. `ros2 topic echo` cannot decode the custom message, because the SDK generates no Python bindings |
| 2026-09-13 | `--method docker` with an SDK image built from that SDK (on an Ubuntu base at the time), result deployed to the board | 15 s cold, 9 s incremental. `talker` runs at 2 Hz, 26.5 MB RSS |
| 2026-09-13 | `--method docker` with the bitbake dev container, colcon-buildx running as a normal user, result deployed to the board | 16 s cold, 9 s incremental. `talker` runs at 2 Hz, 26.5 MB RSS, and here `ros2 topic echo /num` does decode the custom message |
| 2026-09-13 | An interactive SSH session to the board | Died after about 18 s with `Broken pipe` until `IPQoS none` was set in the board's `sshd_config`; commands without a terminal were unaffected. The rebuilt image contains the setting, which was confirmed by reading the image |

## Published Yocto images, 2026-09-15

`k26-oesdk-jazzy` and `rpi5-oesdk-jazzy` were rebuilt on their dev containers from SDKs
built without debug packages, and published alongside `k26-yocto-jazzy` and
`rpi5-yocto-jazzy`.

| Date | What was run | Result |
|---|---|---|
| 2026-09-15 | Both SDK images on an arm64 Linux host, demo workspace | 15 s cold, 8 s incremental. Neither image contains a package manager (no apt, dpkg, rpm or opkg), and `/etc/issue` names the meta-ros distro |
| 2026-09-15 | `k26-oesdk-jazzy`, `k26-yocto-jazzy` and `rpi5-yocto-jazzy`, pulled from the registry onto an Apple Silicon Mac, demo workspace | All three build it; the output is aarch64 and owned by the invoking user |

Not done: re-running the output of the trimmed SDKs on the KV260 (only debug packages
were dropped, so the libraries are those of the 2026-09-13 runs), and running
`rpi5-oesdk-jazzy` from a Mac.

## Raspberry Pi 5, Yocto

| Date | What was run | Result |
|---|---|---|
| 2026-09 | `rpi5-yocto-jazzy` on an arm64 Linux host, demo workspace | 16 s cold, 9 s incremental; the result is an aarch64 binary that does not need `libatomic` |
| 2026-09-15 | `rpi5-oesdk-jazzy` on an arm64 Linux host, demo workspace | Builds |

Nothing has been run on a Raspberry Pi 5 board. The board image, the SDK and both
images exist; only the board step is missing.

## Kria K26 and Pynq on Ubuntu

No dated record. The earlier README text listed the Ubuntu-based K26 images
(`k26-jazzy`, `k26-humble`) as tested on a Kria K26, and the Pynq images and packages as
built and tested against the PYNQ v3.1.1 SD-card image on Pynq-Z1 and Pynq-Z2, both for
Humble and Jazzy. Neither claim recorded a date or a procedure, so they are repeated
here as they stand rather than as verification records.

## Raspberry Pi OS and Debian

The `rpi-*` images and packages have not been run on a board. The dependency lists were
checked by installing each package in a clean `debian:<suite>-slim` container and
running `ros2 topic echo` against a talker; no date was recorded for that either.

## Hosts

| Host | Status |
|---|---|
| arm64 Linux | Every Yocto route above was run there |
| Apple Silicon Mac | The dev containers and `k26-oesdk-jazzy` were run from one (2026-09-15) |
| x86_64 | The Yocto images under QEMU have not been tried. The Pynq and 32-bit Debian images are built on x86_64 runners in CI, which exercises the emulation but not colcon-buildx |

## Image sizes

Measured on 2026-09-15, on the published images. They change with every rebuild, so treat them as orders of magnitude rather than exact figures.

| Image | Download | Unpacked |
|---|---|---|
| `k26-yocto-jazzy` | 215 MB | 1.38 GB |
| `rpi5-yocto-jazzy` | 232 MB | 1.41 GB |
| `k26-oesdk-jazzy` | 830 MB (215 MB dev container + 617 MB SDK layer) | |
| `rpi5-oesdk-jazzy` | 950 MB (232 MB + 717 MB) | |

If you already have the dev container, an SDK image costs only its own layer.

The SDKs are built without debug packages (`SDKIMAGE_FEATURES = "dev-pkgs"`). With the default `dev-pkgs dbg-pkgs src-pkgs`, debug symbols were 72 % of the KV260 SDK's target sysroot and debug sources another 8 %: the installer was 1.1 GB instead of 272 MB, and the resulting K26 image about 10 GB. See [Rebuild the Yocto images](../maintain/yocto.md).

## Adding a record

Add a row with the date, exactly what was run and what happened, and update that
target's `tested` entry in
[`targets.yml`](https://github.com/smarobix/smarobix-buildx-images/blob/main/targets.yml)
so the generated reference agrees. An empty `tested` means "built, not run on hardware",
which is the honest state for most targets.
