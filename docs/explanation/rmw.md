# Why Cyclone DDS

ROS 2 talks over a middleware that is chosen at run time. This project recommends
Cyclone DDS, `rmw_cyclonedds_cpp`, on **every** target: the Pynq boards, the Raspberry
Pi and Debian boards, the Kria K26 on Ubuntu and the Yocto boards alike.

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

## Why

- **Memory.** Cyclone DDS has a markedly smaller footprint than Fast DDS. On a
  Pynq-Z1 or Z2, with 512 MB of RAM for the whole system, that is the difference
  between comfortable and tight, and a 32-bit Raspberry Pi is not much better off.
- **One answer everywhere.** Nodes using different RMW implementations are not
  guaranteed to hear each other, so a fleet with a per-board rule eventually has two
  machines that cannot talk. Recommending the same implementation on every target
  removes that class of problem, and removes the need to remember which board got which.

Earlier documentation recommended Fast DDS on the 64-bit boards and Cyclone DDS on the
small ones. That is no longer the recommendation anywhere here.

## What is installed, and what sets it

Both Fast DDS and Cyclone DDS are built into the `.deb` install trees, and nothing in
them sets `RMW_IMPLEMENTATION`. Unset, ROS 2 uses its own default, which is Fast DDS.
So the choice is yours to make, in every shell that runs a node:

- Export it per shell, as above, or add the line to `~/.bashrc`.
- For a node started by systemd, put it in the unit: `Environment=RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`.
- Set it the same way on every machine in the system, including your laptop.

Where the middleware comes from differs by target:

| Target | Cyclone DDS comes from |
|---|---|
| Pynq, Raspberry Pi OS / Debian | the `.deb` install tree; both implementations are in it |
| Kria K26 on Ubuntu | packages.ros.org: `sudo apt install ros-<distro>-rmw-cyclonedds-cpp` |
| Yocto / meta-ros | the board image; meta-ros installs both with `rmw-implementation` |

The `.deb` prints the recommendation when it is configured, because installing is the
moment a user reliably reads anything about the package. The packages from release
v1.1.0 still print the older, per-architecture advice; this page is the current one.

## Zenoh

`rmw_zenoh` is not in scope yet. The open ARMv7 issues upstream would leave it working
on some of the targets here and not others, which is exactly the split the single
recommendation above avoids. It will be added once those are resolved.

## See also

- [.deb packages](../reference/deb-packages.md) for what else is in the tree.
- [Put ROS 2 on a board from a .deb](../tutorials/ros-on-a-board.md) for the whole
  sequence on a real board.
