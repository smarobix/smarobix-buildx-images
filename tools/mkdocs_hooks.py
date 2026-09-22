# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0

"""MkDocs hooks for the documentation site (registered in mkdocs.yml).

MkDocs builds every page's "edit" link from this repository's edit_uri. That
is wrong for two kinds of page:

- tool/ is a copy of smarobix-colcon-buildx's docs/, so its source lives in
  that repository;
- generated pages would send an editor to a file that the next regeneration
  overwrites. The link points at the real source when there is one and is
  dropped otherwise.
"""

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
    'tool/reference/cli.md': None,
    'tool/reference/config-keys.md': None,
}


def on_page_context(context, page, config, nav):
    src = page.file.src_uri
    if src in GENERATED:
        page.edit_url = GENERATED[src]
    elif src.startswith(TOOL_PREFIX):
        page.edit_url = TOOL_EDIT_BASE + src[len(TOOL_PREFIX):]
    return context
