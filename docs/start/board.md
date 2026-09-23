# Put ROS 2 on the board

ROS 2 comes from a different place on each board, and it has to match the board exactly: an install tree only runs against the libraries it was built with. Pick your board below. The commands in this step run **on the board**, over SSH or a serial console.

!!! note "Jazzy and Humble"

    These pages use ROS 2 Jazzy. For Humble, replace `jazzy` with `humble` in every command, image tag and file name. On a Kria K26 that also means Ubuntu 22.04 in place of 24.04. The Yocto images are Jazzy only.

=== "Kria K26 · Ubuntu"

    A KV260 or KR260 running Ubuntu 24.04 gets ROS 2 from the official packages on packages.ros.org. Nothing from this project goes on the board. This is the [official installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) plus the Cyclone DDS middleware, the demo nodes for the check below, and `rsync` for deploying:

    ```bash
    sudo apt install software-properties-common curl
    sudo add-apt-repository universe
    ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | cut -d'"' -f4)
    curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo "$VERSION_CODENAME")_all.deb"
    sudo apt install /tmp/ros2-apt-source.deb
    sudo apt update
    sudo apt install ros-jazzy-ros-base ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-demo-nodes-cpp rsync
    ```

=== "Raspberry Pi · Debian"

    Raspberry Pi OS and Debian have no ROS 2 packages of their own, so this project builds ROS 2 once per Debian release and architecture and ships it as a `.deb`. The packages are not interchangeable, so ask the board what it runs:

    ```bash
    . /etc/os-release && echo "$VERSION_CODENAME"   # trixie or bookworm
    dpkg --print-architecture                       # arm64 or armhf
    ```

    Then download and install the matching package. Use `apt install ./file.deb`, not `dpkg -i`: the package declares real dependencies, and `dpkg -i` installs none of them.

    === "64-bit · trixie"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-trixie_{{ version }}_arm64.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-trixie_{{ version }}_arm64.deb
        ```

    === "64-bit · bookworm"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-bookworm_{{ version }}_arm64.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-bookworm_{{ version }}_arm64.deb
        ```

    === "32-bit · trixie"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-trixie_{{ version }}_armhf.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-trixie_{{ version }}_armhf.deb
        ```

    === "32-bit · bookworm"

        ```bash
        sudo apt update
        wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-rpi-bookworm_{{ version }}_armhf.deb
        sudo apt install ./smarobix-ros-jazzy-rpi-bookworm_{{ version }}_armhf.deb
        ```

    Nothing in the packages is specific to the Raspberry Pi: they run on any Debian board of the same release and architecture. The 32-bit packages are built for ARMv7, so they run on a Pi 2 and newer, but not on a Pi 1, Zero or Zero W.

=== "Pynq-Z1 / Z2"

    A Pynq-Z1 or Pynq-Z2 running the PYNQ v3.1.1 image (Ubuntu 22.04, 32-bit) gets ROS 2 as a `.deb` built against that image. Check that the card was written from v3.1.1 (the [PYNQ releases page](https://github.com/Xilinx/PYNQ/releases) says which image is which), then, as the `xilinx` user:

    ```bash
    sudo apt update
    wget https://github.com/smarobix/smarobix-buildx-images/releases/download/v{{ version }}/smarobix-ros-jazzy-pynq-v3.1.1_{{ version }}_armhf.deb
    sudo apt install ./smarobix-ros-jazzy-pynq-v3.1.1_{{ version }}_armhf.deb
    ```

    Use `apt install ./file.deb`, not `dpkg -i`: the package declares real dependencies, and `dpkg -i` installs none of them.

=== "Yocto"

    On a Kria K26 or Raspberry Pi 5 running the Yocto image built from this project's `yocto/` configuration, ROS 2 is part of the board image and there is nothing to install. Board images are not published; [Yocto boards](../guides/yocto.md) shows how to build and flash one. Come back here once the board boots.

    The image logs in as `root` with an empty password, which is fine on a bench and nowhere else. It has no bash, only BusyBox `ash`, so the setup script is `setup.sh`:

    ```sh
    . /opt/ros/jazzy/setup.sh
    ```

## Check it

In one shell on the board, source ROS 2, choose the middleware and start the talker:

```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 run demo_nodes_cpp talker
```

In a second shell, after the same two lines, `ros2 run demo_nodes_cpp listener` prints `I heard: [Hello World: 1]` and counts up. A Yocto board has no demo nodes; there, `ros2 pkg list` after `. /opt/ros/jazzy/setup.sh` is the check.

Both Fast DDS and Cyclone DDS are installed and nothing sets `RMW_IMPLEMENTATION`, so export it in every shell that runs a node, on every machine. Cyclone DDS is the recommendation on every board ([why](../how-it-works.md#one-middleware-cyclone-dds)); if a package's install message says otherwise, it is from an older release. Add both lines to `~/.bashrc` to make them stick.

## Next

[Build your workspace](build.md).
