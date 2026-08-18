#!/bin/bash
# Print a Debian Depends: field for the ROS install tree at /opt/ros/$DISTRO.
#
# Runs *inside* the built image, where the tree's own libraries resolve and the
# exact runtime packages it linked against are installed. Every ELF object in
# the tree is resolved with ldd; anything landing outside /opt/ros is an
# external library, and dpkg tells us which package owns it.
#
# This replaces a hand-maintained list, which drifts and understates the truth:
# an earlier version listed only libc6/libpython/libstdc++ and silently omitted
# libopencv-imgcodecs, libssl, libsqlite3, libtinyxml2, libyaml, libzstd, liblz4,
# libacl1 and liblttng-ust — all of which the tree loads at runtime. On a Lite
# board image those are absent, so that .deb would install and then fail on the
# first `ros2` call.
#
# dpkg-shlibdeps would be the orthodox tool, but it chokes on this tree: ROS
# libraries use $ORIGIN RPATHs and unversioned sonames, which it cannot map.
set -euo pipefail

ROOT="/opt/ros/${DISTRO}"

# Scan the whole tree, not just lib/ and bin/. Python extension modules live
# under lib/pythonX.Y/site-packages/<pkg>/, and they pull in libraries nothing
# else does — cv_bridge's boost extension needs libboost_python, which a
# top-level-only scan misses entirely.
mapfile -t ELF < <(
    find "$ROOT" -type f 2>/dev/null | while read -r f; do
        [ "$(head -c4 "$f" | tr -d '\0')" = $'\x7fELF' ] && echo "$f"
    done
)

if [ ${#ELF[@]} -eq 0 ]; then
    echo "compute-depends: no ELF objects found under $ROOT" >&2
    exit 1
fi

# Collect the DIRECT dependencies (DT_NEEDED) of every object. Deliberately not
# ldd: ldd reports the whole transitive closure, which for this tree pulls in
# GDAL, HDF5, Poppler and ~130 packages by way of OpenCV. A Debian package
# declares only what its own objects link against and lets apt resolve the rest
# through those packages' Depends.
mapfile -t SONAMES < <(
    printf '%s\n' "${ELF[@]}" \
        | xargs -r -n64 objdump -p 2>/dev/null \
        | awk '/NEEDED/ { print $2 }' \
        | sort -u
)

# Drop sonames satisfied by the install tree itself. Match on basename anywhere
# in the tree, since ROS libraries are not all directly under lib/.
mapfile -t OWN < <(find "$ROOT" -type f -name '*.so*' -printf '%f\n' 2>/dev/null | sort -u)

EXTERNAL=()
for so in "${SONAMES[@]}"; do
    found=0
    for own in "${OWN[@]}"; do
        [ "$so" = "$own" ] && { found=1; break; }
    done
    [ $found -eq 0 ] && EXTERNAL+=("$so")
done

if [ ${#EXTERNAL[@]} -eq 0 ]; then
    echo "compute-depends: no external sonames found" >&2
    exit 1
fi

# Resolve each soname to a file via the dynamic linker cache, then canonicalise:
# ldconfig reports /lib/... but on a usrmerge system dpkg only knows the file as
# /usr/lib/..., and the soname is a symlink to the versioned file the package
# actually ships.
: > /tmp/external-libs.txt
for so in "${EXTERNAL[@]}"; do
    path=$(ldconfig -p | awk -v s="$so" '$1 == s { print $NF; exit }')
    [ -n "$path" ] && realpath "$path" >> /tmp/external-libs.txt
done
sort -u -o /tmp/external-libs.txt /tmp/external-libs.txt

if [ ! -s /tmp/external-libs.txt ]; then
    echo "compute-depends: resolved no external libraries" >&2
    exit 1
fi

# Map each library to its owning package. dpkg -S prints "pkg: /path" (or a
# comma-separated list, and arch-qualified as "libc6:arm64"), plus "diversion
# by ..." lines that are not packages. A lookup miss is not fatal.
DEPS=$(
    while read -r lib; do
        dpkg -S "$lib" 2>/dev/null || true
    done < /tmp/external-libs.txt \
        | grep -v '^diversion' \
        | sed 's/:[[:space:]].*//' \
        | tr ',' '\n' \
        | sed 's/[[:space:]]//g' \
        | sed 's/:[a-z0-9][a-z0-9-]*$//' \
        | grep -v '^$' \
        | sort -u \
        | paste -sd, - \
        | sed 's/,/, /g'
)

if [ -z "$DEPS" ]; then
    echo "compute-depends: no owning packages resolved" >&2
    exit 1
fi

echo "$DEPS"
