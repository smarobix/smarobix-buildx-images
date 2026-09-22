# colcon-buildx on meta-ros

ROS 2 Jazzy · Yocto scarthgap · Kria K26 and Raspberry Pi 5

One ROS 2 workspace, built three ways for a board running the meta-ros Yocto image, then run on a Kria KV260. Everything below uses public repositories and published images, so all of it is reproducible.

- colcon-buildx: <https://github.com/smarobix/smarobix-colcon-buildx>
- Images and Yocto configuration: <https://github.com/smarobix/smarobix-buildx-images>
- Published images: [`ghcr.io/smarobix/smarobix-buildx-images`](https://github.com/smarobix/smarobix-buildx-images/pkgs/container/smarobix-buildx-images)
- What has been run on hardware, and when: [Tested hardware](../reference/tested-hardware.md)

## What you need

- **Docker** for the two image routes. The published images are `linux/arm64`, so they run natively on an Apple Silicon Mac or arm64 Linux. On an x86_64 host they run under QEMU; see [below](#on-an-x86_64-host).
- **An arm64 Linux host** for the SDK-on-the-host route. The SDK's host tools are built for the machine that ran bitbake, which was aarch64.
- **A board running the Yocto image** built from the same configuration: `ros-image-core` for a KV260, KR260 or Pi 5. Board images aren't published; [step 5](#5-rebuild-the-images-yourself) builds them.

### On an x86_64 host

Register QEMU for arm64 once, then check that an arm64 container runs. Docker Desktop already includes this. [Build on an x86_64 host](../how-to/build-on-x86_64.md) has more.

```bash
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
docker run --rm --platform linux/arm64 alpine uname -m   # aarch64
```

Before the first build with an SDK image, pull it for arm64 explicitly. colcon-buildx starts SDK images without `--platform`, and the tag has only an arm64 entry, so a plain pull on x86_64 fails with "no matching manifest". The dev containers need no extra step.

```bash
docker pull --platform linux/arm64 ghcr.io/smarobix/smarobix-buildx-images:k26-oesdk-jazzy
```

Everything then works as below, only slower, because every compiler process is emulated.

## 1. Install colcon-buildx

The Yocto support is on `main`. The install pulls in `colcon-core` itself.

```bash
pip install "git+https://github.com/smarobix/smarobix-colcon-buildx"
colcon buildx --help
```

If pip refuses because the system Python is externally managed, install it into a virtual environment; [Install](https://smarobix.github.io/smarobix-buildx-images/tool/install/) shows how.

## 2. Create the demo workspace

Two packages, each chosen because it exercises something that broke on the way:

- `demo_msgs` is an interface package, so the rosidl generators must run on the host yet find ament in the target sysroot.
- `demo_node` is an `rclcpp` publisher that finds `demo_msgs`, so the build must find a package the same workspace just built.

Keep that dependency if you swap in a nicer workspace. Without it, a whole class of sysroot bugs goes unseen.

Create both with `ros2 pkg create`:

```bash
mkdir -p yocto_demo_ws/src && cd yocto_demo_ws/src
ros2 pkg create demo_msgs --build-type ament_cmake --license Apache-2.0
ros2 pkg create demo_node --build-type ament_cmake --license Apache-2.0 \
  --dependencies rclcpp demo_msgs --node-name talker
```

If this machine has no ROS 2, run the same two commands in the dev container, from `yocto_demo_ws/src`. On x86_64 this needs the [QEMU setup](#on-an-x86_64-host). `USER` is set because `ros2 pkg create` uses it as the maintainer name, and the container has no account for your uid.

```bash
docker run --rm --platform linux/arm64 --user "$(id -u):$(id -g)" -e HOME=/tmp -e USER="$(id -un)" \
  -v "$PWD:/ws" -w /ws ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy \
  bash -c '. /opt/ros/jazzy/setup.bash &&
    ros2 pkg create demo_msgs --build-type ament_cmake --license Apache-2.0 &&
    ros2 pkg create demo_node --build-type ament_cmake --license Apache-2.0 --dependencies rclcpp demo_msgs --node-name talker'
```

Then change four files. `demo_node`'s `CMakeLists.txt` and `package.xml` need nothing: `--dependencies` and `--node-name` already wire up `rclcpp`, `demo_msgs` and the `talker` executable.

**`demo_msgs/msg/Num.msg`**, a new file:

```text
int64 num
```

**`demo_msgs/CMakeLists.txt`**: add the last two lines here, after `find_package(ament_cmake REQUIRED)`.

```cmake
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg")
```

**`demo_msgs/package.xml`**: add the last three lines here, after the `ament_cmake` build tool dependency.

```xml
<buildtool_depend>ament_cmake</buildtool_depend>
<buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend>
<member_of_group>rosidl_interface_packages</member_of_group>
```

**`demo_node/src/talker.cpp`**: replace the generated hello world with a publisher of `demo_msgs/msg/Num`.

```cpp
#include <chrono>
#include "rclcpp/rclcpp.hpp"
#include "demo_msgs/msg/num.hpp"
using namespace std::chrono_literals;
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto node = rclcpp::Node::make_shared("talker");
  auto pub = node->create_publisher<demo_msgs::msg::Num>("num", 10);
  int64_t n = 0;
  auto timer = node->create_wall_timer(500ms, [&]() {
    demo_msgs::msg::Num m; m.num = n++; pub->publish(m);
    RCLCPP_INFO(node->get_logger(), "published %ld", m.num); });
  rclcpp::spin(node);
  rclcpp::shutdown();
}
```

Go back to `yocto_demo_ws` for the build.

## 3. Build it, any of three ways

Run these from the workspace root. All three link against the meta-ros sysroot, so all three produce binaries for the Yocto image, not for Ubuntu. Output lands in `cross_build/` and `cross_install/`, owned by you.

Each command turns testing off. `ros2 pkg create` adds lint tests, which a cross build can't run. The dev container also ships the linters' CMake hooks without the linters themselves, so configuring with tests on fails there.

### OE-SDK image

`ghcr.io/smarobix/smarobix-buildx-images:k26-oesdk-jazzy` (use `rpi5-oesdk-jazzy` for a Pi 5). Needs Docker; on x86_64, pull it first as [above](#on-an-x86_64-host).

The meta-ros SDK installed on top of the board's dev container (below), so there's no Ubuntu or other distro in it. It cross-compiles on the host architecture, and colcon-buildx recognises it from its labels.

```bash
colcon buildx --method docker \
  --docker-image ghcr.io/smarobix/smarobix-buildx-images:k26-oesdk-jazzy \
  --cmake-args -DBUILD_TESTING=OFF
```

### Dev container built by bitbake

`ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy` (use `rpi5-yocto-jazzy` for a Pi 5). Needs Docker, with QEMU on x86_64.

An aarch64 OCI image of the board's own userspace, plus compilers and `-dev` packages. Bitbake builds it from the same configuration as the board image (recipe `ros-dev-container`). It compiles natively, with no Ubuntu and no cross toolchain, and of the three routes here it is the one that also generates Python message bindings.

```bash
colcon buildx --method docker --docker-platform linux/arm64 \
  --docker-image ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy \
  --cmake-args -DBUILD_TESTING=OFF
```

### SDK installed on the host

`--method sdk`. Needs an arm64 Linux host.

The way meta-ros intends its SDK to be used. Download the installer from the [`yocto-sdk-jazzy-2026.09.15`](https://github.com/smarobix/smarobix-buildx-images/releases/tag/yocto-sdk-jazzy-2026.09.15) release, whose notes list the sha256 of each installer. You can also build it yourself with [step 5](#5-rebuild-the-images-yourself). Install it, then point colcon-buildx at its environment script. The script's name follows the CPU tune: `cortexa72-cortexa53` for the K26, `cortexa76` for the Pi 5.

```bash
R=https://github.com/smarobix/smarobix-buildx-images/releases/download/yocto-sdk-jazzy-2026.09.15
SDK=oecore-ros2-image-sdktest-jazzy-aarch64-cortexa72-cortexa53-k26-smk-kv-sdt-toolchain-nodistro.0.sh
curl -fLO "$R/$SDK"
echo "99529c2bdc3a212585fcd57916865e81178d06e7d3be7e7d396a46a453213335  $SDK" | sha256sum -c -
sh "$SDK" -y -d /opt/ros-sdk
colcon buildx --method sdk \
  --sdk-env /opt/ros-sdk/environment-setup-cortexa72-cortexa53-oe-linux \
  --cmake-args -DBUILD_TESTING=OFF
```

## 4. Deploy and run on the board

The image logs in as `root` with an empty password, which is fine on a bench and nowhere else. It has no bash, only BusyBox `ash`, so source `setup.sh` rather than `setup.bash`. A POSIX shell can't find its own path when sourcing a script, so tell the workspace's `local_setup.sh` where it now lives.

```bash
# from the workspace root on the build host; <board-ip> is the board's address,
# which `ip addr` on the board prints for end0
tar -cf - cross_install \
  | ssh root@<board-ip> 'rm -rf /opt/demo && mkdir -p /opt/demo && tar -C /opt/demo -xf -'
```

```sh
# on the board, in two shells
. /opt/ros/jazzy/setup.sh
COLCON_CURRENT_PREFIX=/opt/demo/cross_install . /opt/demo/cross_install/local_setup.sh

/opt/demo/cross_install/lib/demo_node/talker   # shell 1: publishes /num every 500 ms
ros2 topic echo /num                           # shell 2: dev-container build
ros2 topic info /num                           # shell 2: SDK builds (no Python bindings to decode with)
```

> **If interactive SSH drops after about 18 seconds.** We saw this on a KV260: commands without a terminal worked, but a session with a PTY died with `Broken pipe`. With a PTY, OpenSSH switches to an interactive DSCP marking, and the board's marked replies were lost on the way to the LAN. The images built from `yocto/` set `IPQoS none` in `sshd_config`, which fixes it; setting it on the client side doesn't.

## 5. Rebuild the images yourself

You only need this for the board images, or to rebuild the SDKs and images yourself. The kas files in [`yocto/`](https://github.com/smarobix/smarobix-buildx-images/tree/main/yocto) overlay meta-ros's own `build`-branch kas configs, pinned to the commit these builds used. They add:

- the Kria machines
- the SDK settings
- a small layer (`meta-smrbx`) with the dev-container recipe and the OpenSSH fix

The Pi 5 uses meta-ros's own `oeros-scarthgap-jazzy-raspberrypi5.yml`.

```bash
git clone -b build https://github.com/ros/meta-ros.git meta-ros-build
git -C meta-ros-build checkout 4212d293d5779d3c3b8c445de15066e640d2e601
# copy yocto/kas and yocto/meta-smrbx into place as ../maintain/yocto.md describes, then:
CFG=kas/oeros-scarthgap-jazzy-k26-smk-kv-sdt.yml:kas/smrbx-shared.yml
kas build $CFG                                                  # board image
kas shell $CFG -c 'bitbake ros2-image-sdktest -c populate_sdk'  # SDK
kas shell $CFG -c 'bitbake ros-dev-container'                   # dev container
```

The board image lands in the build directory as
`tmp-glibc/deploy/images/<machine>/ros-image-core-jazzy-<machine>.rootfs.wic.bz2`, with
a `.wic.bmap` beside it, where `<machine>` is `k26-smk-kv-sdt`, `k26-smk-kr-sdt` or
`raspberrypi5`. Write it to an SD card with `bmaptool copy` or any writer that can
unpack bzip2, and boot the board from the card. On a Kria, flash the image that matches
the carrier: U-Boot prints `SCK-KV-G` for a KV260 and `SCK-KR-G` for a KR260. Leave the
QSPI firmware alone unless the card won't boot.

Two settings matter to anyone building a meta-ros SDK for colcon:

- **`TOOLCHAIN_HOST_TASK:append = " nativesdk-ros-sdk-env"`** puts `ros-sdk-env` in the SDK. It's what sets `OE_CMAKE_TOOLCHAIN_FILE`, `PYTHON_SOABI` and `AMENT_PREFIX_PATH`.
- **`SDKIMAGE_FEATURES = "dev-pkgs"`** drops debug symbols and sources, which shrank the K26 installer to about a quarter of its size.

[Rebuilding the Yocto images](../maintain/yocto.md) explains every other setting in the machine files, and how to package an SDK you built as an `oesdk` image.
