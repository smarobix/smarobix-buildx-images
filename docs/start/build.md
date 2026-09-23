# Build your workspace

Back on your computer. This step cross-builds two packages from the official ROS 2 examples, a publisher and a subscriber, in the image that matches your board.

## Create a workspace

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws
git clone -b jazzy --depth 1 https://github.com/ros2/examples.git src/examples
```

## Point colcon-buildx at the board's image

Create `.buildx.conf` in the workspace root, the directory that holds `src/`. `deploy_target` is where the next step copies the result; use your board's user and address.

=== "Kria K26 · Ubuntu"

    ```ini
    method = docker
    docker_image = ghcr.io/smarobix/smarobix-buildx-images:k26-jazzy
    docker_platform = linux/arm64
    deploy_target = ubuntu@10.42.0.3:~/ros2_ws/install/
    ```

    `k26-jazzy` is Ubuntu 24.04 with the same ROS 2 packages as the board, plus a cross toolchain, GStreamer, the Xilinx PPAs and an OpenCV build.

=== "Raspberry Pi · Debian"

    The image has to match the board's Debian release and architecture, as the package did.

    === "64-bit · trixie"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-trixie-jazzy
        docker_platform = linux/arm64
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

    === "64-bit · bookworm"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-arm64-bookworm-jazzy
        docker_platform = linux/arm64
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

    === "32-bit · trixie"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-armv7-trixie-jazzy
        docker_platform = linux/arm/v7
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

    === "32-bit · bookworm"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-armv7-bookworm-jazzy
        docker_platform = linux/arm/v7
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

=== "Pynq-Z1 / Z2"

    ```ini
    method = docker
    docker_image = ghcr.io/smarobix/smarobix-buildx-images:pynq-v3.1.1-jazzy
    docker_platform = linux/arm/v7
    deploy_target = xilinx@192.168.2.99:~/ros2_ws/install/
    ```

    `xilinx` and `192.168.2.99` are the PYNQ image's default user and address.

=== "Yocto"

    Two images exist per board. The dev container below is the board's own userspace plus compilers, and it is the one to start with; the SDK images cross-compile instead, and [Yocto boards](../guides/yocto.md) compares them.

    === "Kria K26"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:k26-yocto-jazzy
        docker_platform = linux/arm64
        deploy_target = root@10.42.0.3:~/ros2_ws/install/
        ```

    === "Raspberry Pi 5"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi5-yocto-jazzy
        docker_platform = linux/arm64
        deploy_target = root@10.42.0.3:~/ros2_ws/install/
        ```

Every image holds the same ROS 2 install tree as the board, so what you build links against what the board has. Every key can also be given on the command line, and the file has a YAML form; the [reference](../tool/reference.md) lists all of them.

## Build

```bash
colcon buildx --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber \
  --cmake-args -DBUILD_TESTING=OFF
```

The first run pulls the image, which takes a few minutes. colcon-buildx then runs `colcon build --merge-install` inside it, with `src/` mounted read-only and the container running as your user, and passes on the arguments it does not handle itself, `--packages-select` and `--cmake-args` among them. `-DBUILD_TESTING=OFF` skips the examples' tests and linters, which a cross build cannot run.

The result lands in `cross_build/` and `cross_install/` next to `src/`, owned by you and kept apart from a native `build/` and `install/`. Check that it is a board binary:

```bash
file cross_install/lib/examples_rclcpp_minimal_publisher/publisher_member_function
```

It says `ARM aarch64` for a 64-bit board and `ARM, EABI5` for a 32-bit one.

Build your own packages the same way: put them in `src/` and drop `--packages-select`. If they need system libraries the board does not have yet, see [Keep the image in step with the board](../guides/sync.md).

## Next

[Deploy and run](deploy.md).
