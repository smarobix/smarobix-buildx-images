# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0

"""MkDocs hooks for the documentation site (registered in mkdocs.yml).

Three jobs:

- Fill in ``{{ version }}`` on every page with the release the site
  documents, so that no page hand-writes a ``.deb`` file name or download
  link for one release. tools/build-site.sh sets BUILDX_VERSION; without it
  the newest ``v*`` tag of this repository is used, so ``mkdocs serve`` works
  from a clone. A page that still holds the placeholder raises a warning,
  which fails a ``--strict`` build.
- Drop the tool/ section from the nav when colcon-buildx's docs are not
  present. build-site.sh copies them in before the build; without them a nav
  entry for a missing file fails ``--strict``.
- Point the edit links of tool/ pages at colcon-buildx, and drop them for
  generated pages, which the next regeneration would overwrite.
"""

import logging
import os
import re
import subprocess
from pathlib import Path

log = logging.getLogger("mkdocs.hooks.buildx")

VERSION = re.compile(r"\{\{\s*version\s*\}\}")
RELEASE_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")

TOOL_PREFIX = 'tool/'
TOOL_EDIT_BASE = (
    'https://github.com/smarobix/smarobix-colcon-buildx/edit/main/docs/')

# Generated pages, keyed by path under docs/. The value is the edit URL of the
# file they are generated from, or None for no edit link.
GENERATED = {
    'reference/targets.md':
        'https://github.com/smarobix/smarobix-buildx-images/edit/main/'
        'targets.yml',
    # Written by colcon-buildx's tools/gen_docs.py from its code.
    'tool/reference.md': None,
}


def _newest_release_tag(repo):
    """The newest v* tag by version number, or '' when there is none."""
    try:
        tags = subprocess.run(
            ["git", "tag", "--list", "v*"], cwd=repo,
            capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return ""
    releases = [t for t in tags if RELEASE_TAG.fullmatch(t)]
    return max(releases, default="",
               key=lambda t: [int(n) for n in RELEASE_TAG.fullmatch(t).groups()])


def on_config(config):
    repo = Path(config['config_file_path']).parent
    version = os.environ.get("BUILDX_VERSION") or _newest_release_tag(repo)
    version = version[1:] if version.startswith("v") else version
    if version:
        log.info("buildx: documenting release v%s", version)
    else:
        log.warning("buildx: no release to document; set BUILDX_VERSION or "
                    "fetch the v* tags")
    config['extra']['buildx_version'] = version

    docs_dir = Path(config['docs_dir'])
    if not (docs_dir / TOOL_PREFIX / 'reference.md').is_file():
        if config.get('nav'):
            config['nav'] = _without_tool(config['nav'])
            # info, not warning: --strict turns warnings into failures, and
            # build-site.sh already says this on its own line.
            log.info(
                'no docs/tool/: building without the colcon-buildx pages')
    return config


def _without_tool(items):
    kept = []
    for item in items:
        if isinstance(item, dict):
            (title, value), = item.items()
            if isinstance(value, str):
                if value.startswith(TOOL_PREFIX):
                    continue
            else:
                value = _without_tool(value)
                if not value:
                    continue
                item = {title: value}
        elif isinstance(item, str) and item.startswith(TOOL_PREFIX):
            continue
        kept.append(item)
    return kept


def on_page_markdown(markdown, page, config, files):
    version = config['extra'].get('buildx_version')
    if version:
        return VERSION.sub(version, markdown)
    if VERSION.search(markdown):
        log.warning("buildx: %s: {{ version }} left unresolved",
                    page.file.src_uri)
    return markdown


def on_page_context(context, page, config, nav):
    src = page.file.src_uri
    if src in GENERATED:
        page.edit_url = GENERATED[src]
    elif src.startswith(TOOL_PREFIX):
        page.edit_url = TOOL_EDIT_BASE + src[len(TOOL_PREFIX):]
    return context
