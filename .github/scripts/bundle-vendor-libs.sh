#!/bin/bash
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
#
# Copy the libraries an install tree links from outside the distribution into
# the tree itself, so the .deb built from it is complete.
#
# The Pynq images build OpenCV from source into /opt/install, because the
# vendor runtime pins versions that jammy's apt OpenCV does not match. The
# install tree links that build: libcv_bridge.so and cv_bridge's Python
# extension need libopencv_core.so.413, libopencv_imgproc.so.413 and
# libopencv_imgcodecs.so.413. /opt/install is not part of /opt/ros/<distro>,
# so the package shipped neither those files nor a dependency on anything that
# provides them, and no board has an OpenCV with that soname: PYNQ v3.1.1 is
# Ubuntu 22.04, whose OpenCV is 4.5. cv_bridge therefore failed to load on
# every board that installed the package (issue #20).
#
# Copying them into <tree>/lib is what makes the package self-contained. ROS's
# own setup.sh puts that directory on LD_LIBRARY_PATH, so the loader finds them
# without an RPATH or an ldconfig entry, and nothing outside a sourced ROS
# environment sees them. Running before compute-depends.sh also means the
# libraries the vendor build itself needs — libpng, libjpeg, libtiff and the
# rest — are derived from the tree like any other dependency, instead of being
# invisible.
#
# The Debian images have nothing to copy: they link the OpenCV that apt
# installs, which the package already depends on. The script is a no-op there.
set -euo pipefail

DISTRO=${DISTRO:?DISTRO must be set}
TREE=/opt/ros/${DISTRO}
# Prefixes that hold libraries built from source, outside any package.
VENDOR_DIRS=${VENDOR_DIRS:-/opt/install/lib}

[ -d "$TREE" ] || { echo "no install tree at $TREE" >&2; exit 1; }
mkdir -p "$TREE/lib"

# Sonames every ELF object in the tree asks for, directly.
needed() {
    find "$TREE" -type f \( -name '*.so' -o -name '*.so.*' \) -print0 \
        | xargs -0 -r -n1 objdump -p 2>/dev/null \
        | awk '/NEEDED/ { print $2 }' | sort -u
}

# Sonames the tree already carries, by file name.
provided() {
    find "$TREE" -type f -o -type l | sed 's|.*/||' | sort -u
}

copied_any=1
rounds=0
total=0
while [ "$copied_any" -eq 1 ]; do
    copied_any=0
    rounds=$((rounds + 1))
    if [ "$rounds" -gt 10 ]; then
        echo "giving up after 10 rounds: a vendor library cycle?" >&2
        exit 1
    fi
    # Captured first: a failure inside the pipeline would otherwise read as
    # "nothing is missing" and ship the same broken package as before.
    missing=$(comm -23 <(needed) <(provided))
    for soname in $missing; do
        for dir in $VENDOR_DIRS; do
            src="${dir}/${soname}"
            [ -e "$src" ] || continue
            real=$(readlink -f "$src")
            cp -a "$real" "$TREE/lib/"
            if [ "$(basename "$real")" != "$soname" ]; then
                ln -sfn "$(basename "$real")" "$TREE/lib/${soname}"
            fi
            echo "bundled ${soname} -> $(basename "$real") (from ${dir})"
            copied_any=1
            total=$((total + 1))
            break
        done
    done
done

echo "bundled ${total} vendor library file(s) into ${TREE}/lib"

# What is still missing comes from packages on the board, and
# compute-depends.sh turns it into the .deb's Depends field. Listing it here
# makes a surprise visible in the job log.
echo "external sonames left for compute-depends.sh:" >&2
comm -23 <(needed) <(provided) | tr '\n' ' ' >&2
echo >&2
