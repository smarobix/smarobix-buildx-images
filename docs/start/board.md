# Put ROS 2 on the board

ROS 2 comes from a different place on each board, and it has to match the board exactly: an install tree only runs against the libraries it was built with. Pick your board below. The commands in this step run **on the board**, over SSH or a serial console.

=== "OEROS"

    ROS 2 is part of the robot's image, so there is nothing to install. OEROS documents its images in [its repository](https://github.com/oerosproject/meta-oeros/blob/main/docs/containers.md); for a Kria K26 board image, see [Yocto boards](../guides/yocto.md). Come back here once the robot boots.

    Yocto images often have no bash, so use the `.sh` setup script:

    ```sh
    . /opt/ros/lyrical/setup.sh
    ros2 pkg list
    ```

=== "Pynq-Z1 / Z2"

    A Pynq-Z1 or Pynq-Z2 running the PYNQ v3.1.1 image (Ubuntu 22.04, 32-bit) gets ROS 2 as a `.deb` built against that image. Check that the card was written from v3.1.1 (the [PYNQ releases page](https://github.com/Xilinx/PYNQ/releases) says which image is which), then, as the `xilinx` user:

    ```bash
    sudo apt update
    wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-pynq-v3.1.1_{{ version }}_armhf.deb
    sudo apt install ./smarobix-ros-jazzy-pynq-v3.1.1_{{ version }}_armhf.deb
    ```

    Use `apt install ./file.deb`, not `dpkg -i`: the package declares real dependencies, and `dpkg -i` installs none of them.

=== "Raspberry Pi · 32-bit"

    Raspberry Pi OS and Debian have no ROS 2 packages of their own, so this project builds ROS 2 once per Debian release and ships it as a `.deb`. Ask the board which release it runs:

    ```bash
    . /etc/os-release && echo "$VERSION_CODENAME"   # trixie or bookworm
    dpkg --print-architecture                       # armhf
    ```

    === "trixie"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-trixie_{{ version }}_armhf.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-trixie_{{ version }}_armhf.deb
        ```

    === "bookworm"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-bookworm_{{ version }}_armhf.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-bookworm_{{ version }}_armhf.deb
        ```

    Use `apt install ./file.deb`, not `dpkg -i`: the package declares real dependencies, and `dpkg -i` installs none of them. Nothing in the packages is specific to the Raspberry Pi: they run on any 32-bit Debian board of the same release. They are built for ARMv7, so they run on a Pi 2 and newer and a Zero 2 W, but not on a Pi 1, Zero or Zero W.

!!! note "Humble"

    For ROS 2 Humble on a 32-bit board, replace `jazzy` with `humble` in every command, image tag and file name.

## Check it

On a 32-bit board, in one shell, source ROS 2, choose the middleware and start the talker:

```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 run demo_nodes_cpp talker
```

In a second shell, after the same two lines, `ros2 run demo_nodes_cpp listener` prints `I heard: [Hello World: 1]` and counts up. On an OEROS robot, `ros2 pkg list` above is the check.

Both Fast DDS and Cyclone DDS are in the `.deb` and nothing sets `RMW_IMPLEMENTATION`, so export it in every shell that runs a node, on every machine. Cyclone DDS is the recommendation ([why](../how-it-works.md#one-middleware-cyclone-dds)). Add both lines to `~/.bashrc` to make them stick.

## Next

[Build your workspace](build.md).
