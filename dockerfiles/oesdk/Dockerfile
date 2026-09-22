# syntax=docker/dockerfile:1
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
#
# Cross-build image built from a meta-ros Yocto SDK, for any board meta-ros
# builds for (tested: Kria K26 KV260/KR260 and Raspberry Pi 5).
#
# Unlike the other images in this repo, this one does not build natively as the
# target architecture. It carries a cross toolchain plus the target sysroot, and
# colcon-buildx recognises it by the org.smarobix.buildx.* labels below: it
# skips --platform, sources the SDK environment, and applies its toolchain
# wrapper.
#
# The base is the board's own dev container (yocto/meta-smrbx, recipe
# ros-dev-container), which bitbake builds from the same configuration as the
# board image and the SDK. There is no Ubuntu or other distro underneath. The
# SDK brings its own glibc, python3, colcon, CMake and ninja; the dev container
# provides the shell, xz, file and python3 the installer needs.
#
# The SDK's host tools are aarch64 binaries (the SDK was built on an arm64 host),
# so the image is linux/arm64 only: native on Apple Silicon and on arm64 Linux.
#
# The SDK must be built from ros2-image-sdktest with
#     TOOLCHAIN_HOST_TASK:append = " nativesdk-ros-sdk-env"
# as yocto/kas/smrbx-shared.yml does. Nothing in meta-ros pulls ros-sdk-env in
# on its own, and without it the SDK cannot configure a ROS workspace.
#
# Build, passing the directory that holds the installer as the "sdk" context:
#     docker buildx build --platform linux/arm64 --load \
#       --build-context sdk=/path/to/installer/dir \
#       --build-arg BASE_IMAGE=ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy \
#       --build-arg SDK_INSTALLER=oecore-ros2-image-sdktest-...-toolchain-nodistro.0.sh \
#       --build-arg SDK_ENV_SETUP=environment-setup-cortexa72-cortexa53-oe-linux \
#       -t k26-oesdk:jazzy dockerfiles/oesdk
# SDK_ENV_SETUP names the SDK's environment script, which follows the target
# tune: cortexa72-cortexa53 for the Kria K26, cortexa76 for the Raspberry Pi 5.
# CI downloads the installers from this repository's releases.

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG SDK_INSTALLER
ARG SDK_ENV_SETUP
ARG SDK_PREFIX=/opt/ros-sdk
ARG ROS_DISTRO=jazzy
ARG TARGET_PLATFORM=linux/arm64

# Bind-mounted rather than COPY'd, so the installer does not stay behind in a
# layer underneath the installed SDK.
RUN --mount=type=bind,from=sdk,target=/sdk \
    test -n "${SDK_INSTALLER}" && test -n "${SDK_ENV_SETUP}" \
 && sh "/sdk/${SDK_INSTALLER}" -y -d "${SDK_PREFIX}" \
 && test -f "${SDK_PREFIX}/${SDK_ENV_SETUP}"

# Replaces the base's org.smarobix.buildx.kind=yocto-native, so colcon-buildx
# treats this as an SDK image rather than a native one.
LABEL org.smarobix.buildx.kind="oe-sdk" \
      org.smarobix.buildx.env-setup="${SDK_PREFIX}/${SDK_ENV_SETUP}" \
      org.smarobix.buildx.target-platform="${TARGET_PLATFORM}" \
      org.smarobix.buildx.ros-distro="${ROS_DISTRO}"
