# Build your workspace

Back on your computer. This step builds two packages from the official ROS 2 examples, a publisher and a subscriber, for your board.

## Create a workspace

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws
git clone -b jazzy --depth 1 https://github.com/ros2/examples.git src/examples
```

For an OEROS robot, clone `-b lyrical` instead: OEROS publishes ROS 2 Lyrical.

## Point colcon buildx at the image

Create `.buildx.conf` in the workspace root, the directory that holds `src/`. `deploy_target` is where the next step copies the result; use your board's user and address.

=== "OEROS"

    The image depends on your computer; [OEROS robots](../tool/oeros.md#pick-an-image) explains why.

    === "x86_64 computer"

        ```ini
        method = docker
        docker_image = ghcr.io/oerosproject/oeros-sdk-cross:lyrical-arm64
        deploy_target = root@my-robot.local:/opt/ws/install/
        ```

    === "arm64 computer"

        ```ini
        method = docker
        docker_image = ghcr.io/oerosproject/oeros-sdk-target:lyrical-arm64
        deploy_target = root@my-robot.local:/opt/ws/install/
        ```

=== "Pynq-Z1 / Z2"

    ```ini
    method = docker
    docker_image = ghcr.io/smarobix/smarobix-buildx-images:pynq-v3.1.1-jazzy
    deploy_target = xilinx@192.168.2.99:~/ros2_ws/install/
    ```

    `xilinx` and `192.168.2.99` are the PYNQ image's default user and address.

=== "Raspberry Pi · 32-bit"

    The image has to match the board's Debian release, as the package did.

    === "trixie"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-armv7-trixie-jazzy
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

    === "bookworm"

        ```ini
        method = docker
        docker_image = ghcr.io/smarobix/smarobix-buildx-images:rpi-armv7-bookworm-jazzy
        deploy_target = pi@10.42.0.3:~/ros2_ws/install/
        ```

A board image holds the same ROS 2 install tree as the board, and an OEROS SDK image the robot's own libraries, so what you build links against what the board has. Every key can also be given on the command line, and the file has a YAML form; the [reference](../tool/reference.md) lists all of them.

## Build

```bash
colcon buildx --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber \
  --cmake-args -DBUILD_TESTING=OFF
```

The first run pulls the image, then prepares it or builds its cross image, once per image version. colcon buildx then runs `colcon build --merge-install` on your computer's own architecture, with `src/` mounted read-only and the container running as your user, and passes on the arguments it does not handle itself, `--packages-select` and `--cmake-args` among them. `-DBUILD_TESTING=OFF` skips the examples' tests and linters, which a cross build cannot run.

The result lands in `cross_build/` and `cross_install/` next to `src/`, owned by you and kept apart from a native `build/` and `install/`. Check that it is a board binary:

```bash
file cross_install/lib/examples_rclcpp_minimal_publisher/publisher_member_function
```

It says `ARM aarch64` for an OEROS robot and `ARM, EABI5` for a 32-bit board.

Build your own packages the same way: put them in `src/` and drop `--packages-select`. A system library they need has to be on the board, and so in its image. For an OEROS robot, see [Dependencies](../tool/oeros.md#dependencies). For a 32-bit board, install the package on the board, and build an image of your own `FROM` the published one with the same `apt-get install`, then name it in `docker_image`. Building that image runs the board's apt, so on an x86_64 computer it needs QEMU, as this project's CI does; colcon buildx itself never does.

## Next

[Deploy and run](deploy.md).
