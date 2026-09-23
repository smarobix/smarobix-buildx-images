# Deploy and run

`--deploy` copies `cross_install/` to `deploy_target` after a successful build, with `rsync --delete`. Create the directory on the board once, with your board's user and address, then build again with `--deploy`:

```bash
ssh ubuntu@10.42.0.3 mkdir -p ros2_ws/install
colcon buildx --deploy --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber \
  --cmake-args -DBUILD_TESTING=OFF
```

The build has nothing left to do, so it finishes at once and then runs the rsync. `--delete` removes anything in the target directory that the build did not produce, so point `deploy_target` at a directory that holds nothing else, never at a home directory or `/opt/ros`. Both ends need `rsync`, and SSH keys spare you a password prompt per run.

## Run it on the board

Source ROS 2, then the workspace, then choose the middleware. In one shell on the board:

=== "Ubuntu, Debian or PYNQ"

    ```bash
    source /opt/ros/jazzy/setup.bash
    source ~/ros2_ws/install/local_setup.bash
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    ros2 run examples_rclcpp_minimal_publisher publisher_member_function
    ```

=== "Yocto"

    The image has no bash, so use the `.sh` scripts. A POSIX shell cannot tell where a sourced script lives, so tell the workspace's script where it landed:

    ```sh
    . /opt/ros/jazzy/setup.sh
    COLCON_CURRENT_PREFIX=$HOME/ros2_ws/install . $HOME/ros2_ws/install/local_setup.sh
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    $HOME/ros2_ws/install/lib/examples_rclcpp_minimal_publisher/publisher_member_function
    ```

In a second shell, after the same setup lines, run the subscriber the same way (`examples_rclcpp_minimal_subscriber`, `subscriber_member_function`). The publisher prints `Publishing: 'Hello, world! 0'` and counts up; the subscriber prints `I heard: 'Hello, world! 0'` for each message. Both shells need the same `RMW_IMPLEMENTATION`.

## From here

- **Your own packages.** Put them in `src/` and drop `--packages-select`. `deploy = true` in `.buildx.conf` deploys after every build.
- **System dependencies** that the board does not have yet: [Keep the image in step with the board](../guides/sync.md).
- **Yocto boards** have two more ways to build: [Yocto boards](../guides/yocto.md).
- **Every option and config key:** the [reference](../tool/reference.md). **Something failed:** [Troubleshooting](../tool/troubleshooting.md).
