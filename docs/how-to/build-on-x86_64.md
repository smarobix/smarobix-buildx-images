# Build on an x86_64 host

Most images here run *as* the target board: they hold an arm64 or ARMv7 userspace, and
Docker runs them through QEMU on a host of another architecture. That works on x86_64,
but it needs the emulation registered once, and the SDK images need one extra step.

An arm64 Linux host or an Apple Silicon Mac needs none of this for arm64 images.

## Register QEMU once

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Docker Desktop already includes the handlers, so this is only needed on a plain Docker
install. Check that it took:

```bash
docker run --rm --platform linux/arm64 alpine uname -m    # aarch64
docker run --rm --platform linux/arm/v7 alpine uname -m   # armv7l
```

The registration is kernel state and is lost on reboot. Run the command again after
one, or install the distribution package that registers the handlers at boot.

If a build stops with `exec format error`, the handlers are not registered.

## Then build as usual

```bash
colcon buildx
```

Nothing else changes. Everything is slower, because every compiler process is emulated;
a large workspace can take several times as long as on an arm64 host.

## Pull an SDK image before the first build with it

The Yocto SDK images (`k26-oesdk-jazzy`, `rpi5-oesdk-jazzy`) run on the *host*
architecture rather than the board's, so colcon-buildx starts them without
`--platform`. Their tag has only an arm64 entry, so on x86_64 a plain pull fails with
"no matching manifest". Pull them for arm64 explicitly first:

```bash
docker pull --platform linux/arm64 ghcr.io/smarobix/smarobix-buildx-images:k26-oesdk-jazzy
```

Do it again whenever the tag is updated, since the tags are rolling. The dev containers
(`k26-yocto-jazzy`, `rpi5-yocto-jazzy`) need no extra step: colcon-buildx passes
`--docker-platform` for them.

An SDK image pulled this way runs its cross toolchain under emulation, which is the
slowest of the three Yocto routes on an x86_64 host. Nobody has run either Yocto image
on x86_64 yet; see [Tested hardware](../reference/tested-hardware.md).

## What QEMU cannot do for you

- `--method sdk`, the SDK installed on the host, needs an arm64 Linux host. The
  published SDKs' host tools are aarch64 binaries. An x86_64 SDK would have to be built
  with `SDKMACHINE = "x86_64"`.
- An ARMv7 image on an arm64 host is not automatically native either. Several recent
  arm64 CPUs, Apple Silicon among them, cannot execute 32-bit ARM code, so `armhf`
  targets go through QEMU there as well.

## See also

- [Native or cross](../explanation/native-vs-cross.md), for what the two kinds of image
  do differently.
- [Troubleshooting](https://smarobix.github.io/smarobix-buildx-images/tool/troubleshooting/)
  in the colcon-buildx docs.
