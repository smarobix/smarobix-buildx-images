# Native or cross

The images here work in two different ways, and `colcon buildx` treats them
differently. Most of them run *as* the board and compile natively, emulated if the host
is another architecture. The two Yocto SDK images carry a cross toolchain and run on the
host. Both produce binaries for the board; what differs is speed, what is in the image,
and what comes out.

## Native under QEMU

`k26-*`, `pynq-v3.1.1-*`, `rpi-*` and the Yocto dev containers (`k26-yocto-jazzy`,
`rpi5-yocto-jazzy`) hold the board's own userspace: its libc, its Python, its ROS 2
install tree. Docker runs them with `--platform linux/arm64` or `--platform
linux/arm/v7`, natively when the host matches and through QEMU when it does not.
Inside, the compiler is an ordinary native compiler and the build is an ordinary build.

- Nothing has to be told where the sysroot is, because the sysroot is the whole
  container.
- Everything ROS 2 generates works, including Python message bindings for your own
  interface packages.
- On a host of another architecture every compiler process is emulated, which is the
  slow part. An `armhf` image is emulated on most arm64 hosts too, since several recent
  arm64 CPUs cannot execute 32-bit ARM code.

See [Build on an x86_64 host](../how-to/build-on-x86_64.md) for the QEMU setup.

## Cross with an SDK image

`k26-oesdk-jazzy` and `rpi5-oesdk-jazzy` are the meta-ros Yocto SDK installed on top of
the board's dev container. The SDK is a cross toolchain plus the target sysroot, so the
image runs on the *host* architecture and produces board binaries without emulating
anything. The published ones have aarch64 host tools, so they run natively on arm64
hosts.

What that costs:

- **No Python message bindings.** meta-ros SDKs ship no `rosidl_generator_py`, so an
  interface package gets C and C++ bindings only. On the board, `ros2 topic echo` can
  then see a custom message but not decode it. The dev container does generate them.
- **Ninja, not make.** The SDK ships `ninja`, `cmake`, `pkg-config`, `python3` and
  `colcon`, but no `make`, so colcon-buildx builds with Ninja unless you pick a
  generator yourself.
- **One more layer to download.** An SDK image is the dev container plus the SDK, so if
  you already have the dev container you only fetch the SDK layer.

## How colcon-buildx tells them apart

By image labels, not by tag. The label contract belongs to colcon-buildx, which reads
it; the full definition is in
[Image labels](https://smarobix.github.io/smarobix-buildx-images/tool/reference/labels/).
In short:

- `org.smarobix.buildx.kind` says what kind of image it is. Absent means the default,
  `ros-apt`: run it as the target, emulated if needed. `oe-sdk` means a cross SDK image:
  skip `--platform`, source the SDK environment and apply the toolchain wrapper.
  `yocto-native` is what the bitbake dev container sets, and is currently handled like
  the default.
- `org.smarobix.buildx.env-setup` is the path of the SDK environment script, or several
  separated by colons.
- `org.smarobix.buildx.target-platform` and `org.smarobix.buildx.ros-distro` record what
  the image targets, for example `linux/arm64` and `jazzy`.

So an SDK image needs no special flags: `colcon buildx --method docker --docker-image
<sdk image>` is enough, and the tool works out the rest.

## Which to use

For a Yocto board, either works and both were measured at much the same speed on an
arm64 host ([Tested hardware](../reference/tested-hardware.md)). Use the dev container
if your workspace has interface packages whose Python bindings you want on the board, or
if you want the build to be as close to the board as possible. Use the SDK image if you
want a genuine cross build, or if you are on a host where emulation would be the
bottleneck.

For every other board there is only the native kind.

## Without colcon-buildx

Nothing stops you using an image directly; colcon-buildx exists to get the details
right, not to hide them.

```bash
docker run --rm --platform linux/arm64 \
  -v "$PWD:/workspace" -w /workspace \
  ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy \
  bash -c 'source /opt/ros/jazzy/setup.bash && colcon build --merge-install'
```

What you give up: the container runs as root, so the output is root-owned; the build and
install directories are the native ones, so they collide with a host build; and an SDK
image needs its environment script sourced and a toolchain file that the stock one
cannot supply.
