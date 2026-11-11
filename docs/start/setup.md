# Set up your computer

Everything in these pages runs on your computer, except the commands marked as running on the board. You need Docker, Python 3, `git` and `rsync`, and SSH access to the board.

## Docker

Install Docker Desktop, or Docker Engine on Linux. That is all: any computer works, x86_64 or arm64, and nothing runs under emulation, so there is no QEMU to set up.

colcon buildx builds on your computer's own architecture. For a robot's SDK image, it adds a thin layer the first time it meets that image version; for a board image of another architecture, it builds a cross image from it, once. Both need network access the first time, and take from a few seconds to about a minute.

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
