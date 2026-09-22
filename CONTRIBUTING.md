# Contributing

Thanks for wanting to help. This page covers the mechanics. How the repository actually works is in [docs/maintain/](docs/maintain/index.md):

| Page | Subject |
|---|---|
| [Add a board](docs/maintain/add-a-board.md) | Deciding what kind of target a board is, and adding it to `targets.yml` |
| [Add a downstream version](docs/maintain/add-a-downstream-version.md) | A new PYNQ or Debian release |
| [Base images and source fixes](docs/maintain/base-images.md) | Matching the board's ABI, and the patches older ROS source needs |
| [`.deb` dependencies](docs/maintain/deb-dependencies.md) | How `Depends` is computed, and the fields kept by hand |
| [CI and releases](docs/maintain/ci-and-releases.md) | What each event builds, and how to cut a release |
| [Rebuild the Yocto images](docs/maintain/yocto.md) | The kas configuration, the SDK and the dev containers |

## Propose a change

Open an issue before the pull request for anything larger than a typo, and say what you want to run where. For a new board that means: the board and its SoC, the OS release (`cat /etc/os-release`), the architecture (`dpkg --print-architecture`), the ROS 2 distro, and whether packages.ros.org publishes binaries for that pair. [Add a board](docs/maintain/add-a-board.md) has the one-line check for the last point.

Then open a pull request against `main`, one topic per pull request, in small commits that each make sense on their own.

A pull request builds only the images whose inputs it changed, and never pushes anything. A change to `targets.yml` or to `build-images.yml` builds all of them. [CI and releases](docs/maintain/ci-and-releases.md) explains what is and is not covered by that build.

## Licensing of contributions

This repository is under the Apache License 2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). As section 5 of that licence puts it, any contribution you intentionally submit for inclusion in the work is under its terms, without any additional conditions. There is no separate contributor agreement.

Everything under [`yocto/`](yocto/) is MIT instead, following the OpenEmbedded and meta-ros convention.

## Licence headers

Every new source file starts with an SPDX header: Python, shell, Dockerfiles, workflow and kas YAML, bitbake recipes and appends, CMake, JavaScript and CSS.

```
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
```

Use `MIT` in place of `Apache-2.0` under `yocto/`. The header goes after a shebang, and after the `# syntax=` parser directive in a Dockerfile, which has to stay on the first line.

Markdown, JSON and the files that Dockerfiles `COPY` into an image are covered by [`REUSE.toml`](REUSE.toml) instead. Don't add headers to those: new bytes in a `COPY`'d file change the layer checksum and rebuild ROS 2 from source in every image built from that directory.

`reuse lint` runs in CI on every pull request and on `main`. To run it locally:

```bash
pipx run reuse lint
```

## Commit messages

Use the prefixes the history uses: `docs:`, `fix:`, `ci:`, `chore:`, `feat:`, `refactor:`, `test:`, with an optional scope such as `feat(rpi):`. The subject is imperative and lowercase after the prefix. The body explains why the change is needed, and names the failure that prompted it if there was one.

```
fix(ci): snapshot ldconfig once in compute-depends to avoid a SIGPIPE race

Piping `ldconfig -p` into an awk that exits on the first match makes
ldconfig die of SIGPIPE. Under `set -o pipefail` that surfaces as exit
141 and kills the script, and whether it happens is a timing race.
```

## Two habits that keep this repository readable

- **Comments explain why.** The reason a workaround exists stays next to the code it protects, with the failure it prevents. What the code does should be visible from the code.
- **Each fact has one owner.** Board names, image tags, `.deb` names, the RMW recommendation and the tested status all live in [`targets.yml`](targets.yml). `docs/reference/targets.md` is generated from it by `tools/targets.py` and is never edited by hand; other pages link to it rather than repeating it.
