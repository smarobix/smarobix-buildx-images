# Set up your computer

Everything in these pages runs on your computer, except the commands marked as running on the board. You need Docker, Python 3, `git` and `rsync`, and SSH access to the board.

## Docker

Install Docker Desktop, or Docker Engine on Linux. Most build images run *as* the board: they hold an arm64 or ARMv7 userspace, so the host has to be able to run that architecture.

- An **Apple Silicon Mac or an arm64 Linux host** runs arm64 images natively. Nothing to do.
- An **x86_64 host** needs QEMU registered with the kernel. Docker Desktop includes it. On Docker Engine, register it once, and again after a reboot:

    ```bash
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    ```

- **32-bit images** (`linux/arm/v7`: the Pynq and the 32-bit Raspberry Pi targets) go through QEMU on most arm64 hosts too, Apple Silicon included. The same command registers it.

Check that it took:

```bash
docker run --rm --platform linux/arm64 alpine uname -m    # aarch64
docker run --rm --platform linux/arm/v7 alpine uname -m   # armv7l
```

Emulated builds work. They are several times slower than native ones, because every compiler process is emulated. `exec format error` means the handlers are not registered.

## colcon-buildx

colcon-buildx is a Python package that plugs into colcon as a verb. Install it into a virtual environment; Debian, Ubuntu and Homebrew all refuse to let pip modify the system Python.

```bash
python3 -m venv ~/.venvs/buildx
. ~/.venvs/buildx/bin/activate
pip install "git+https://github.com/smarobix/smarobix-colcon-buildx"
colcon buildx --help
```

Activate the environment in every shell you build from. It needs Python 3.9 or newer, and the install pulls in `colcon-core`, `colcon-cmake` and PyYAML.

To work on colcon-buildx itself, clone it and install it with `pip install -e ".[test]"` instead. Its README covers the tests.

## Next

[Put ROS 2 on the board](board.md).
