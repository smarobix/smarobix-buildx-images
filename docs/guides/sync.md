# Keep the image in step with the board

A binary runs on the board only if it was linked against the libraries the board has. Two things break that over time: your packages gain dependencies the board lacks, and the board's packages drift away from the image's through updates and hand installs. colcon-buildx treats the board as the reference and brings the image to it, with three options that talk to the board over SSH.

They work with boards that use apt and dpkg: Ubuntu on a K26, Raspberry Pi OS and Debian, and PYNQ. Use SSH keys; each run opens several connections.

```bash
# 1. bring the board up to date
ssh ubuntu@10.42.0.3 'sudo apt-get update && sudo apt-get upgrade -y'

# 2. install the workspace's dependencies on the board
colcon buildx --install-deps-on-device ubuntu@10.42.0.3

# 3. make a copy of the image whose packages match the board
colcon buildx --sync-from-device ubuntu@10.42.0.3

# 4. build; the synced copy is picked up on its own
colcon buildx
```

## What each option does

**`--install-deps-on-device`** copies `src/` to the board, runs `rosdep install` there for everything the `package.xml` files declare, and exits without building. The board needs `rsync`, `python3-rosdep` and `sudo`, which may ask for a password.

**`--sync-from-device`** lists the packages installed on the board and in the image, installs the board's versions into a container of the image, downgrading where needed, adds what is only on the board, and commits the result as a local image `<tag>-synced-<YYYYMMDD>`. Nothing is pushed anywhere. It writes `.buildx-sync-manifest.json` and a log under `cross_log/` into the workspace root; add both to `.gitignore`.

**Every later build** uses the newest `<tag>-synced-*` image for the configured tag and says so with `Using synced image:`. To build in the published tag once, pass `--use-base-image`; to go back for good, delete the synced images with `docker rmi`. After changing `docker_image`, sync again.

Both are one-off actions, so they cannot be set in a config file; a file that names them gets a warning and the build goes ahead.

## What not to do

`--install-deps` without `-on-device` installs into a copy of the image only. The build then links against libraries the board does not have, and the binary fails there. Use it for dependencies the board already has, or follow it with a sync.

Neither option applies to the Yocto SDK images or to `--method sdk`: their libraries come from the SDK's sysroot, fixed when the SDK was built. Add the dependency to the Yocto image and rebuild the SDK instead.
