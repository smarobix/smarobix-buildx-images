# Contributing

Thanks for wanting to help. This page covers the mechanics; how the repository works is in [Maintaining](docs/maintain/index.md).

## Propose a change

Open an issue before the pull request for anything larger than a typo, and say what you want to run where. For a new board that means: the board and its SoC, the OS release (`cat /etc/os-release`), the architecture (`dpkg --print-architecture`), the ROS 2 distro, and whether packages.ros.org publishes binaries for that pair ([how to check](docs/how-it-works.md#why-these-boards-need-help)).

Then open a pull request against `main`, one topic per pull request, in small commits that each make sense on their own. A pull request builds only the images whose inputs it changed, and never pushes anything; a change to `targets.yml` or to the workflow builds all of them.

## Licensing

This repository is under the Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). As section 5 of that licence puts it, any contribution you intentionally submit for inclusion is under its terms, without additional conditions. There is no separate contributor agreement. Everything under [`yocto/`](yocto/) is MIT instead, following the OpenEmbedded and meta-ros convention.

Every new source file starts with an SPDX header, after a shebang or a Dockerfile's `# syntax=` line:

```
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
```

Use `MIT` under `yocto/`. Markdown, JSON and the files that Dockerfiles `COPY` into an image are covered by [`REUSE.toml`](REUSE.toml) instead; don't add headers to those, because new bytes in a `COPY`'d file rebuild ROS 2 from source in every image built from that directory. `reuse lint` runs in CI; locally, `pipx run reuse lint`.

## Commit messages

Use the prefixes the history uses, `docs:`, `fix:`, `ci:`, `chore:`, `feat:`, `refactor:`, `test:`, with an optional scope such as `feat(rpi):`. The subject is imperative and lowercase after the prefix. The body explains why the change is needed, and names the failure that prompted it if there was one.

## Two habits that keep this repository readable

- **Comments explain why.** The reason a workaround exists stays next to the code it protects, with the failure it prevents. What the code does should be visible from the code.
- **Each fact has one owner.** Board names, image tags, `.deb` names and the tested status live in [`targets.yml`](targets.yml). `docs/reference/targets.md` is generated from it and never edited by hand; other pages link to it rather than repeating it, and `python3 tools/targets.py check-docs` fails on a page that names a tag or package the file does not define.
