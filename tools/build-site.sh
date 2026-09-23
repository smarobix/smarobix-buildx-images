#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
#
# Assemble and build the documentation site.
#
#   tools/build-site.sh [VERSION]
#
# VERSION is the release the site documents, as v1.1.0 or 1.1.0. Without it the
# script uses $BUILDX_VERSION, and without that the newest v* release from the
# GitHub API. tools/mkdocs_hooks.py fills it into every "{{ version }}" on the
# pages, so every .deb link and file name on the site comes from it.
#
# Environment:
#   BUILDX_VERSION  the release to document, as above
#   CBX_DOCS_DIR    smarobix-colcon-buildx's docs/ directory; without it the
#                   script shallow-clones the repository
#   GITHUB_TOKEN    raises the rate limit of the release lookup
#   SITE_DIR        output directory (default: site)
#
# docs/tool/ is written here and ignored by git. It is left in place
# afterwards, so "mkdocs serve" gives a local preview.

set -euo pipefail

REPO=smarobix/smarobix-buildx-images
CBX_REPO=https://github.com/smarobix/smarobix-colcon-buildx

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"

note() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# The newest v* release. The API's "latest" flag is no use: hand-made
# yocto-sdk-* releases share the release stream and one of them can hold it,
# so filter by tag name instead. One page of 100 covers every release so far.
latest_release() {
    local url="https://api.github.com/repos/$REPO/releases?per_page=100"
    local -a auth=()
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
    fi
    curl -fsSL -H 'Accept: application/vnd.github+json' \
        ${auth[@]+"${auth[@]}"} "$url" | python3 -c '
import json, re, sys

releases = json.load(sys.stdin)
tags = [r["tag_name"] for r in releases
        if r["tag_name"].startswith("v")
        and not r.get("draft") and not r.get("prerelease")]
# Newest by version number, not by date: releases can be published in any order.
print(max(tags, key=lambda t: [int(n) for n in re.findall(r"[0-9]+", t)], default=""))
'
}

# (a) Which release the site documents. The hook reads BUILDX_VERSION.
version=${1:-${BUILDX_VERSION:-}}
if [ -z "$version" ]; then
    note "looking up the newest v* release of $REPO"
    version=$(latest_release)
    [ -n "$version" ] || die "no v* release found; pass the version as an argument"
fi
version=${version#v}
[[ $version =~ ^[0-9]+(\.[0-9]+)*$ ]] || die "not a version number: $version"
note "documenting release v$version"
export BUILDX_VERSION=$version

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# (b) colcon-buildx's docs, which the site serves under tool/.
if [ -n "${CBX_DOCS_DIR:-}" ]; then
    cbx_docs=$CBX_DOCS_DIR
    note "taking colcon-buildx's docs from $cbx_docs"
else
    note "cloning colcon-buildx"
    git clone --quiet --depth 1 --branch main "$CBX_REPO" "$tmp/colcon-buildx"
    note "colcon-buildx at $(git -C "$tmp/colcon-buildx" rev-parse --short HEAD)"
    cbx_docs=$tmp/colcon-buildx/docs
fi
case "$(cd -- "$cbx_docs" && pwd -P)" in
    "$repo_root"/docs/tool*) die "CBX_DOCS_DIR must not be inside docs/tool" ;;
esac
rm -rf docs/tool
if [ -f "$cbx_docs/reference.md" ]; then
    mkdir -p docs/tool
    cp -R "$cbx_docs"/. docs/tool/
elif [ -n "${CBX_DOCS_DIR:-}" ]; then
    # An explicit directory that isn't colcon-buildx's docs is a mistake.
    die "no reference.md in $cbx_docs: not colcon-buildx's docs directory"
else
    # colcon-buildx's docs/ arrives with its own pull request. Until then,
    # build the rest of the site rather than failing: the hook drops the
    # tool/ pages from the nav, and they come back once that branch is merged.
    note "colcon-buildx has no docs/reference.md yet; building without its pages"
fi

# (c) No page may name an image tag or package that targets.yml doesn't have.
note "checking the docs against targets.yml"
python3 tools/targets.py check-docs docs README.md CONTRIBUTING.md

# (d) The site itself. --strict turns every warning, a broken link above all,
# into a failed build.
command -v mkdocs > /dev/null || die "mkdocs is missing: pip install -r docs/requirements.txt"
note "building the site"
mkdocs build --strict --site-dir "${SITE_DIR:-site}"
