SUMMARY = "Native ROS 2 build container, from the same build as the board image"
DESCRIPTION = "An aarch64 OCI image of the meta-ros userspace with compilers and \
development headers. colcon-buildx builds inside it natively (its --method docker \
path for images that run as the target architecture), so workspaces are compiled \
against exactly the libraries the board image ships -- no Ubuntu, no cross toolchain."
LICENSE = "MIT"

# image-oci's "oci" type depends on OE-core's "container" type
# (IMAGE_TYPEDEP:oci = "container tar.bz2"), which image-container provides.
inherit core-image image-container image-oci
inherit ros_distro_${ROS_DISTRO}
inherit ${ROS_DISTRO_TYPE}_image

IMAGE_FSTYPES = "oci"
# smrbx-shared.yml appends wic.bz2/wic.bmap for the board images, and an :append
# lands after this assignment. A disk image of a container rootfs is useless.
IMAGE_FSTYPES:remove = "wic.bz2 wic.bmap"

# image-container refuses to build unless the kernel provider is linux-dummy. The
# container installs no kernel at all; the machine's real kernel is still needed
# by the board image built from the same configuration, so opt out of the check.
IMAGE_CONTAINER_NO_DUMMY = "1"

# tools-sdk: compilers, make, binutils for the target. dev-pkgs: the -dev
# (headers, CMake configs) of everything installed, which is what a build needs.
IMAGE_FEATURES += "tools-sdk dev-pkgs"

# No packagegroup-core-boot: a container needs no init system or kernel. That
# also drops busybox, so the shell tools builds call out to are listed explicitly.
# xz: dockerfiles/oesdk builds the SDK image on this container, and the SDK
# installer's payload is xz-compressed.
# python-cmake-module: rosidl_generator_py find_package()s it; without it every
# interface package fails to configure (meta-ros's ros2-image-sdktest lists it too).
IMAGE_INSTALL = " \
    bash \
    coreutils \
    sed \
    grep \
    gawk \
    tar \
    gzip \
    xz \
    which \
    cmake \
    ninja \
    python3-colcon-common-extensions \
    python-cmake-module \
    ros-core \
    ${ROS_SDK_TARGET_PACKAGES} \
"

# Link the way the distro does. rcutils exports "-latomic" to every package that
# uses it; OE builds (and the SDK's environment) link with --as-needed, so the
# unused libatomic is dropped. Without these flags the container kept it as a hard
# dependency, and binaries failed on the board, which does not ship libatomic.
# One token: OCI_IMAGE_ENV_VARS is space-separated.
OCI_IMAGE_ENV_VARS = "LDFLAGS=-Wl,-O1,--hash-style=gnu,--as-needed"

# colcon-buildx runs `docker run IMAGE bash -c '...'`. image-oci's default
# entrypoint is "sh", which would turn that into `sh bash -c ...`.
OCI_IMAGE_ENTRYPOINT = ""
OCI_IMAGE_TAG = "${ROS_DISTRO}"
# Space-separated key=value pairs; values must not contain spaces.
OCI_IMAGE_LABELS = " \
    org.smarobix.buildx.kind=yocto-native \
    org.smarobix.buildx.ros-distro=${ROS_DISTRO} \
    org.smarobix.buildx.target-platform=linux/arm64 \
"
