# Rebuild the Yocto images

Four things are built from `yocto/`: the board image, which is not published; the SDK installer, a release asset; the dev container, pushed to GHCR by hand; and, in CI from the first two, the SDK cross image. [Yocto boards](../guides/yocto.md) sets up the kas build and produces the board image. This page is the rest. Every unusual setting in the kas files and in `ros-dev-container.bb` has a comment saying which failure it prevents.

## The SDK and the dev container

From the same `CFG` as the board image:

```bash
kas shell $CFG -c 'bitbake ros2-image-sdktest -c populate_sdk'   # SDK installer
kas shell $CFG -c 'bitbake ros-dev-container'                    # OCI dev container
```

The SDK must come from `ros2-image-sdktest`, with `nativesdk-ros-sdk-env` in `TOOLCHAIN_HOST_TASK`, which `smrbx-shared.yml` adds; without `ros-sdk-env` an SDK cannot configure a ROS workspace. `SDKIMAGE_FEATURES = "dev-pkgs"` there drops debug symbols and sources, which were four fifths of the installer.

## Publish the dev container

Bitbake's OCI archive records only the tag as its name, so load it through `skopeo`:

```bash
D=<build dir>/tmp-glibc/deploy/images/k26-smk-kv-sdt
docker run --rm --user $(id -u):$(id -g) -v "$D:/in:ro" -v /tmp:/out quay.io/skopeo/stable \
  copy oci-archive:/in/ros-dev-container-jazzy-jazzy-oci.tar:jazzy docker-archive:/out/devctr.tar:ros-dev-container:jazzy
docker load -i /tmp/devctr.tar
docker tag ros-dev-container:jazzy ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy
```

Push it with a throwaway Docker configuration, so the token never lands in `~/.docker`:

```bash
export DOCKER_CONFIG=$(mktemp -d)
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin   # a token with write:packages
docker push ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy
docker logout ghcr.io && rm -rf "$DOCKER_CONFIG" && unset DOCKER_CONFIG
```

CI does not build these on purpose: a job that reached into a build host's downloads and sstate would be reproducible nowhere else. Their `targets.yml` entries have `build: null` and `published: manual`. The SDK images build `FROM` this tag, so afterwards start a build on `main` with `gh workflow run build-images.yml --ref main`.

## Publish the SDK

Create a `yocto-sdk-<distro>-<date>` release with `--latest=false` and the installers as assets, listing each sha256 in the notes ([why](index.md#cut-a-release)). Then point the `oe-sdk` entries in `targets.yml` at the new release, installer names and checksums. That pull request builds every image, and the `oe-sdk` jobs download and verify the installer.

To build an SDK image locally, pass the installer's directory as the `sdk` build context, so the installer never lands in a layer:

```bash
docker buildx build --platform linux/arm64 --load --build-context sdk=/path/to/installer/dir \
  --build-arg BASE_IMAGE=ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy \
  --build-arg SDK_INSTALLER=oecore-ros2-image-sdktest-jazzy-aarch64-cortexa72-cortexa53-k26-smk-kv-sdt-toolchain-nodistro.0.sh \
  --build-arg SDK_ENV_SETUP=environment-setup-cortexa72-cortexa53-oe-linux \
  -t buildx-local:k26-oesdk-jazzy dockerfiles/oesdk
```

The published SDKs are `linux/arm64` only, because their host tools are aarch64 binaries. An x86_64 variant needs an SDK built with `SDKMACHINE = "x86_64"` on an x86_64 base image.
