#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
"""Validate targets.yml and generate everything that is derived from it.

targets.yml describes every published image tag once. This script checks it
and turns it into:

    matrix build|package       the job matrices of build-images.yml (JSON)
    docs [-o FILE] [--check]   docs/reference/targets.md
    check-docs PATH...         fails on image tags or .deb names in markdown
                               that targets.yml does not define

The documentation site fills "{{ version }}" on every page with the release
it documents (tools/mkdocs_hooks.py), so a .deb file name in a page may carry
that placeholder; check-docs reads it as a version.

Every subcommand validates targets.yml first and exits 1, listing every
problem it found, if the file is not valid. Needs Python 3.8+ and PyYAML.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the environment
    sys.exit("tools/targets.py needs PyYAML (pip install PyYAML, or apt install python3-yaml)")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT / "targets.yml"

# family: (heading, what the reader needs to know about it). The order here is
# the order of docs/reference/targets.md.
FAMILIES = {
    "ubuntu-apt": (
        "Ubuntu with the official ROS 2 packages",
        "ROS 2 on the board comes from the official apt packages at packages.ros.org. "
        "These images are for cross-building your workspace; no `.deb` is published.",
    ),
    "pynq": (
        "PYNQ",
        "ROS 2 is built from source against the PYNQ SD-card image the tag names, and "
        "published as a `.deb` for the board.",
    ),
    "debian": (
        "Raspberry Pi OS and Debian",
        "Debian has no official ROS 2 binaries, so ROS 2 is built from source on stock "
        "Debian, per suite and architecture, and published as a `.deb`. Nothing in these "
        "images is specific to the Raspberry Pi.",
    ),
    "yocto-native": (
        "Yocto dev containers",
        "The board's own meta-ros userspace plus compilers, built by bitbake from the "
        "same configuration as the board image and pushed by hand. They run as the "
        "target. ROS 2 on the board is part of the Yocto board image, which is not "
        "published.",
    ),
    "oe-sdk": (
        "Yocto SDK cross images",
        "The meta-ros SDK installed on top of the matching dev container. The image "
        "carries a cross toolchain and runs on the host rather than as the target, so it "
        "has no target platform and is started without `--platform`. The tag has only a "
        "`linux/arm64` image; on an x86_64 host, pull it with `--platform linux/arm64` "
        "first.",
    ),
}

# Docker platform -> dpkg architecture of the userspace in such an image.
PLATFORM_ARCH = {
    "linux/arm64": "arm64",
    "linux/arm/v7": "armhf",
    "linux/amd64": "amd64",
}

PUBLISHED = ("ci", "manual")

TOP_KEYS = {"repository", "targets"}
TARGET_REQUIRED = {"id", "image", "distro", "family", "board", "boards", "os", "arch",
                   "platform", "rmw", "build", "tested"}
TARGET_OPTIONAL = {"published", "deb"}
OS_KEYS = {"name", "codename"}
BUILD_REQUIRED = {"dir", "dockerfile", "runs_on"}
BUILD_OPTIONAL = {"args", "platform", "sdk"}
SDK_KEYS = {"base_image", "release", "installer", "sha256", "env_setup"}
DEB_KEYS = {"pkg", "target", "depends_extra", "recommends", "suggests"}
TESTED_KEYS = {"board", "date", "note"}

# The release placeholder the site build fills in; check-docs treats it as a
# version so that the file name around it is still checked.
VERSION_PLACEHOLDER = re.compile(r"\{\{\s*version\s*\}\}")
# Characters that make a mention in the docs a placeholder or a pattern
# (`<tag>`, `${TAG}`, `rpi-*`, `k26-…`) rather than a real name.
PLACEHOLDER = re.compile(r"[<>{}*$…]|\.\.\.")
# Where a name in markdown ends: whitespace, quotes, brackets, table pipes;
# for a package name also a slash, since it is often the end of a URL.
TAG_CHARS = r"[^\s`'\"()\[\]|]*"
PKG_CHARS = r"[^\s`'\"()\[\]|/]*"
TRAILING = ".,;:!?"


class TargetsError(Exception):
    """targets.yml is not valid. args[0] is the list of problems."""

    def __init__(self, problems):
        super().__init__(problems)
        self.problems = list(problems)

    def __str__(self):
        return "\n".join(self.problems)


class _Loader(yaml.SafeLoader):
    """A SafeLoader that rejects duplicate mapping keys.

    Plain PyYAML keeps the last of two equal keys, so a pasted second `deb:`
    would silently replace the first.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=True)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


# --------------------------------------------------------------------------
# Loading and validation


def load(path=DEFAULT_FILE, root=ROOT, check_files=True):
    """Read and validate targets.yml. Returns the dict produced by validate()."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.load(f, Loader=_Loader)  # noqa: S506 - SafeLoader subclass
    except OSError as e:
        raise TargetsError([f"{path}: {e.strerror}"])
    except yaml.YAMLError as e:
        raise TargetsError([f"{path}: {e}"])
    return validate(data, root=root, check_files=check_files, name=path.name)


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _check_keys(problems, where, mapping, required, optional=frozenset()):
    missing = sorted(required - mapping.keys())
    unknown = sorted(mapping.keys() - required - optional)
    if missing:
        problems.append(f"{where}: missing {', '.join(missing)}")
    if unknown:
        problems.append(f"{where}: unknown key {', '.join(map(str, unknown))}")


def _date(v):
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        datetime.date.fromisoformat(v)  # raises on 2026-13-01
        return v
    raise ValueError(v)


def validate(data, root=ROOT, check_files=True, name="targets.yml"):
    """Check the parsed targets.yml and return it normalised.

    The result is {"repository", "registry", "targets": [...]}, where every
    target has `published`, `deb` (None when absent) and a `build` whose
    `args` is a dict, and dates are ISO strings. Raises TargetsError listing
    every problem found.
    """
    problems = []
    if not isinstance(data, dict):
        raise TargetsError([f"{name}: expected a mapping at the top level"])
    _check_keys(problems, name, {k: v for k, v in data.items() if not str(k).startswith("x-")},
                TOP_KEYS)
    repository = data.get("repository")
    if not (_is_str(repository) and re.fullmatch(r"[\w.-]+/[\w.-]+", repository)):
        problems.append(f"{name}: repository must be owner/name, not {repository!r}")
        repository = "invalid/invalid"
    raw = data.get("targets")
    if not isinstance(raw, list) or not raw:
        problems.append(f"{name}: targets must be a non-empty list")
        raise TargetsError(problems)

    targets = []
    ids = {}
    for i, t in enumerate(raw):
        where = f"{name}: targets[{i}]"
        if not isinstance(t, dict):
            problems.append(f"{where}: expected a mapping")
            continue
        if _is_str(t.get("id")):
            where = f"{name}: {t['id']}"
        before = len(problems)
        _check_keys(problems, where, t, TARGET_REQUIRED, TARGET_OPTIONAL)
        if len(problems) > before:
            continue
        t = dict(t)

        for key in ("id", "image", "distro", "board", "boards", "arch", "rmw"):
            if not _is_str(t[key]):
                problems.append(f"{where}: {key} must be a non-empty string")
        if any(not _is_str(t[k]) for k in ("id", "image", "distro")):
            continue
        if t["id"] != f"{t['image']}-{t['distro']}":
            problems.append(f"{where}: id must be image-distro, {t['image']}-{t['distro']}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", t["id"]):
            problems.append(f"{where}: id is not a valid lower-case image tag")
        if t["id"] in ids:
            problems.append(f"{where}: duplicate id (also targets[{ids[t['id']]}])")
        ids[t["id"]] = i

        family = t["family"]
        if family not in FAMILIES:
            problems.append(f"{where}: unknown family {family!r}; one of {', '.join(FAMILIES)}")

        os_ = t["os"]
        if not isinstance(os_, dict):
            problems.append(f"{where}: os must be a mapping with name and codename")
        else:
            _check_keys(problems, f"{where}: os", os_, OS_KEYS)
            if not all(_is_str(os_.get(k)) for k in OS_KEYS):
                problems.append(f"{where}: os.name and os.codename must be strings")

        platform = t["platform"]
        if platform is None:
            if family != "oe-sdk":
                problems.append(f"{where}: platform is null, which only an oe-sdk target may be")
        elif family == "oe-sdk":
            problems.append(f"{where}: an oe-sdk image runs on the host, so platform must be null")
        elif platform not in PLATFORM_ARCH:
            problems.append(f"{where}: unknown platform {platform!r}; add it to PLATFORM_ARCH")
        elif PLATFORM_ARCH[platform] != t["arch"]:
            problems.append(f"{where}: arch {t['arch']!r} does not match platform {platform}"
                            f" ({PLATFORM_ARCH[platform]})")

        if _is_str(t["rmw"]) and not t["rmw"].startswith("rmw_"):
            problems.append(f"{where}: rmw must name an RMW package such as rmw_cyclonedds_cpp")

        published = t.setdefault("published", "ci")
        build = t["build"]
        if build is None and (family == "oe-sdk" or platform is None):
            problems.append(f"{where}: an oe-sdk target is built in CI from its SDK, so it "
                            f"needs a build")
        if published not in PUBLISHED:
            problems.append(f"{where}: published must be one of {', '.join(PUBLISHED)}")
        elif build is None and published != "manual":
            problems.append(f"{where}: build: null needs published: manual")
        elif build is not None and published != "ci":
            problems.append(f"{where}: published: manual needs build: null")

        if build is not None:
            t["build"] = _validate_build(problems, where, t, build, root, check_files)

        deb = t.get("deb")
        if deb is None:
            t["deb"] = None
        elif not isinstance(deb, dict):
            problems.append(f"{where}: deb must be a mapping")
        else:
            _check_keys(problems, f"{where}: deb", deb, DEB_KEYS)
            for key in sorted(DEB_KEYS & deb.keys()):
                if not _is_str(deb[key]):
                    problems.append(f"{where}: deb.{key} must be a non-empty string")
            if build is None or platform is None:
                problems.append(f"{where}: a deb is cut from the CI-built image, so it needs a "
                                f"build and a platform")
            if _is_str(deb.get("pkg")) and not re.fullmatch(r"[a-z0-9][a-z0-9.+-]*", deb["pkg"]):
                problems.append(f"{where}: deb.pkg is not valid in a Debian package name")
            if _is_str(deb.get("suggests")) and "," in deb["suggests"]:
                problems.append(f"{where}: deb.suggests is space-separated: the postinst pastes "
                                f"it into an apt command")

        tested = t["tested"]
        if not isinstance(tested, list):
            problems.append(f"{where}: tested must be a list (empty: not run on a board yet)")
        else:
            norm = []
            for j, rec in enumerate(tested):
                w = f"{where}: tested[{j}]"
                if not isinstance(rec, dict):
                    problems.append(f"{w}: expected a mapping with board, date and note")
                    continue
                _check_keys(problems, w, rec, TESTED_KEYS)
                if not (_is_str(rec.get("board")) and _is_str(rec.get("note"))):
                    problems.append(f"{w}: board and note must be strings")
                try:
                    date = _date(rec.get("date"))
                except ValueError:
                    problems.append(f"{w}: date must be YYYY-MM-DD")
                    date = None
                norm.append({"board": rec.get("board"), "date": date, "note": rec.get("note")})
            t["tested"] = norm

        targets.append(t)

    # Cross-references between targets.
    for t in targets:
        sdk = (t.get("build") or {}).get("sdk") if isinstance(t.get("build"), dict) else None
        if isinstance(sdk, dict) and sdk.get("base_image") not in ids:
            problems.append(f"{name}: {t['id']}: build.sdk.base_image {sdk.get('base_image')!r} "
                            f"is not a target in this file")

    if problems:
        raise TargetsError(problems)
    return {
        "repository": repository,
        "registry": f"ghcr.io/{repository.lower()}",
        "targets": targets,
    }


def _validate_build(problems, where, t, build, root, check_files):
    w = f"{where}: build"
    if not isinstance(build, dict):
        problems.append(f"{w}: expected a mapping or null")
        return build
    before = len(problems)
    _check_keys(problems, w, build, BUILD_REQUIRED, BUILD_OPTIONAL)
    if len(problems) > before:
        return build
    build = dict(build)
    for key in ("dir", "dockerfile"):
        if not _is_str(build[key]) or "/" in build[key] or build[key].startswith("."):
            problems.append(f"{w}.{key} must be a plain file or directory name")
    runs_on = build["runs_on"]
    if isinstance(runs_on, str):
        runs_on = [runs_on]
    if not (isinstance(runs_on, list) and runs_on and all(_is_str(x) for x in runs_on)):
        problems.append(f"{w}.runs_on must be a runner label or a list of them")

    args = build.setdefault("args", {})
    if not isinstance(args, dict):
        problems.append(f"{w}.args must be a mapping of build-arg names to values")
        build["args"] = {}
    else:
        for k, v in args.items():
            if not (isinstance(k, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k)):
                problems.append(f"{w}.args: {k!r} is not a build-arg name")
            # YAML reads 3.10 as the float 3.1, so a version must be quoted.
            if not isinstance(v, str):
                problems.append(f"{w}.args.{k} must be a quoted string, not {v!r}")

    if t["family"] == "debian" and isinstance(args, dict) and isinstance(t.get("os"), dict):
        if args.get("SUITE") != t["os"].get("codename"):
            problems.append(f"{w}.args.SUITE must equal os.codename ({t['os'].get('codename')})")

    if t["platform"] is None:
        if build.get("platform") not in PLATFORM_ARCH:
            problems.append(f"{w}.platform must name the platform to build for "
                            f"({', '.join(PLATFORM_ARCH)}), since platform is null")
    elif "platform" in build:
        problems.append(f"{w}.platform is only for targets whose platform is null")

    sdk = build.get("sdk")
    if t["family"] == "oe-sdk":
        if not isinstance(sdk, dict):
            problems.append(f"{w}.sdk is required for an oe-sdk target")
        else:
            _check_keys(problems, f"{w}.sdk", sdk, SDK_KEYS)
            for key in sorted(SDK_KEYS & sdk.keys()):
                if not _is_str(sdk[key]):
                    problems.append(f"{w}.sdk.{key} must be a non-empty string")
            if _is_str(sdk.get("sha256")) and not re.fullmatch(r"[0-9a-f]{64}", sdk["sha256"]):
                problems.append(f"{w}.sdk.sha256 must be 64 lower-case hex digits")
    elif sdk is not None:
        problems.append(f"{w}.sdk is only for oe-sdk targets")

    if check_files and _is_str(build["dir"]) and _is_str(build["dockerfile"]):
        dockerfile = Path(root) / "dockerfiles" / build["dir"] / build["dockerfile"]
        if not dockerfile.is_file():
            problems.append(f"{w}: {dockerfile.relative_to(root)} does not exist")
    return build


# --------------------------------------------------------------------------
# Generators


def build_matrix(cfg):
    """The build job's matrix: one entry per target that CI builds.

    The keys are the ones build-images.yml reads. build_args is the list of
    Docker build args from targets.yml, one NAME=value per line; the SDK
    arguments stay separate because BASE_IMAGE needs the registry the
    workflow runs against.
    """
    include = []
    for t in cfg["targets"]:
        b = t["build"]
        if b is None:
            continue
        entry = {
            "board_dir": b["dir"],
            "dockerfile": b["dockerfile"],
            "image": t["image"],
            "distro": t["distro"],
            "platform": t["platform"] or b["platform"],
            "runs_on": b["runs_on"],
            "build_args": "\n".join(f"{k}={v}" for k, v in b["args"].items()),
        }
        sdk = b.get("sdk")
        if sdk:
            entry.update({
                "base_image": sdk["base_image"],
                "sdk_release": sdk["release"],
                "sdk_installer": sdk["installer"],
                "sdk_sha256": sdk["sha256"],
                "sdk_env_setup": sdk["env_setup"],
            })
        include.append(entry)
    return {"include": include}


# Inputs that belong to every image rather than to one of them. A change to
# any of these rebuilds the lot: the workflow decides how each image is built,
# targets.yml decides what is built, and targets.py turns the one into the
# other.
SHARED_INPUTS = (
    ".github/workflows/build-images.yml",
    "targets.yml",
    "tools/targets.py",
)


def select_changed(matrix, changed):
    """Narrow a build matrix to the images a list of changed paths affects.

    `changed` is an iterable of repository-relative paths. Returns the matrix
    unchanged when one of SHARED_INPUTS is among them, because then every
    image's inputs have changed. An image's own inputs are its
    dockerfiles/<board_dir>/ directory.
    """
    changed = [c.strip() for c in changed if c.strip()]
    if any(c in SHARED_INPUTS for c in changed):
        return matrix
    include = [
        entry for entry in matrix["include"]
        if any(c.startswith(f"dockerfiles/{entry['board_dir']}/") for c in changed)
    ]
    return {"include": include}


def package_matrix(cfg):
    """The package job's matrix: one entry per target with a deb block."""
    include = []
    for t in cfg["targets"]:
        deb = t["deb"]
        if deb is None:
            continue
        include.append({
            "image": t["image"],
            "pkg": deb["pkg"],
            "distro": t["distro"],
            "platform": t["platform"],
            "runs_on": t["build"]["runs_on"],
            "deb_arch": t["arch"],
            "target": deb["target"],
            "board": t["boards"],
            "rmw": t["rmw"],
            "depends_extra": deb["depends_extra"],
            "recommends": deb["recommends"],
            "suggests": deb["suggests"],
        })
    return {"include": include}


def package_name(t):
    return f"smarobix-ros-{t['distro']}-{t['deb']['pkg']}"


def _cell(text):
    return str(text).replace("|", "\\|")


def render_docs(cfg):
    """The markdown of docs/reference/targets.md."""
    repo_url = f"https://github.com/{cfg['repository']}"
    registry = cfg["registry"]
    example = cfg["targets"][0]["id"]
    out = [
        "<!-- Generated from targets.yml by tools/targets.py docs. Do not edit. -->",
        "",
        "# Targets",
        "",
        f"Every published image, generated from [`targets.yml`]({repo_url}/blob/main/targets.yml). "
        f"An image is `{registry}:<tag>`, for example `{registry}:{example}`.",
        "",
        "Where a `.deb` package is named, every `v*` "
        f"[release]({repo_url}/releases) attaches it as `<package>_<version>_<arch>.deb`, "
        "next to a `.tar.gz` of the same tree; "
        "[How it works](../how-it-works.md#what-is-in-a-deb) describes the packages. "
        "Tested lists dated runs on real hardware; \"not yet\" means built, but not run on a "
        "board.",
    ]
    for family, (title, blurb) in FAMILIES.items():
        members = [t for t in cfg["targets"] if t["family"] == family]
        if not members:
            continue
        out += ["", f"## {title} (`{family}`)", "", blurb, "",
                "| Tag | Boards | OS | Arch | Docker platform | `.deb` package | Tested |",
                "|---|---|---|---|---|---|---|"]
        for t in members:
            platform = f"`{t['platform']}`" if t["platform"] else "none (runs on the host)"
            deb = f"`{package_name(t)}`" if t["deb"] else "none"
            tested = "; ".join(f"{r['date']}, {r['board']}" for r in t["tested"]) or "not yet"
            os_ = f"{t['os']['name']} (`{t['os']['codename']}`)"
            out.append("| " + " | ".join(_cell(c) for c in (
                f"`{t['id']}`", t["boards"], os_, f"`{t['arch']}`", platform, deb, tested,
            )) + " |")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# check-docs


def _markdown_files(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*.md") if f.is_file())
        elif p.is_file():
            yield p
        else:
            raise TargetsError([f"{p}: no such file or directory"])


def check_docs(cfg, paths):
    """Return 'file:line: problem' for every unknown tag or package name."""
    tags = {t["id"] for t in cfg["targets"]}
    tags |= {f"{t['id']}-buildcache" for t in cfg["targets"] if t["build"] is not None}
    packages = {}
    for t in cfg["targets"]:
        if t["deb"] is not None:
            packages.setdefault(package_name(t), set()).add(t["arch"])
    tag_re = re.compile(re.escape(cfg["registry"]) + ":(" + TAG_CHARS + ")")
    pkg_re = re.compile(r"smarobix-ros-" + PKG_CHARS)

    problems = []
    for path in _markdown_files(paths):
        text = VERSION_PLACEHOLDER.sub("0.0.0", path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in tag_re.finditer(line):
                tag = m.group(1).split("@", 1)[0]
                if PLACEHOLDER.search(tag):
                    continue
                tag = tag.rstrip(TRAILING)
                if tag and tag not in tags:
                    problems.append(f"{path}:{lineno}: unknown image tag {tag!r}")
            for m in pkg_re.finditer(line):
                word = m.group(0)
                if PLACEHOLDER.search(word):
                    continue
                word = word.rstrip(TRAILING)
                name, _, rest = word.partition("_")
                if name not in packages:
                    problems.append(f"{path}:{lineno}: unknown package {name!r}")
                    continue
                # name_version_arch.deb or .tar.gz: the architecture must be one we ship.
                parts = rest.split("_")
                if len(parts) == 2:
                    arch = parts[1].split(".", 1)[0]
                    if arch not in packages[name]:
                        problems.append(f"{path}:{lineno}: {name} is not built for {arch!r}"
                                        f" (only {', '.join(sorted(packages[name]))})")
    return problems


# --------------------------------------------------------------------------
# Command line


def _write(text, output):
    if output is None or output == "-":
        sys.stdout.write(text)
    else:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="targets.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--file", default=str(DEFAULT_FILE),
                        help="targets file (default: targets.yml at the repository root)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("matrix", help="print a job matrix of build-images.yml as JSON")
    p.add_argument("job", choices=("build", "package"))
    p.add_argument("--changed", metavar="FILE",
                   help="file listing the changed paths, one per line ('-' for standard "
                        "input); the build matrix then holds only the images they affect")

    p = sub.add_parser("docs", help="write docs/reference/targets.md")
    p.add_argument("-o", "--output", help="file to write (default: standard output)")
    p.add_argument("--check", action="store_true",
                   help="don't write; fail if --output differs from what would be written")

    p = sub.add_parser("check-docs",
                       help="fail on image tags or .deb names in markdown that targets.yml lacks")
    p.add_argument("paths", nargs="+", metavar="PATH",
                   help="markdown file, or directory to search for *.md")

    args = parser.parse_args(argv)
    try:
        cfg = load(args.file)
        if args.command == "matrix":
            matrix = build_matrix(cfg) if args.job == "build" else package_matrix(cfg)
            # The package job runs on a tag and packages everything, so only
            # the build matrix narrows.
            if args.changed and args.job == "build":
                text = sys.stdin.read() if args.changed == "-" \
                    else Path(args.changed).read_text(encoding="utf-8")
                matrix = select_changed(matrix, text.splitlines())
            # One line: the workflow passes it through $GITHUB_OUTPUT.
            print(json.dumps(matrix, separators=(",", ":")))
        elif args.command == "docs":
            text = render_docs(cfg)
            if args.check:
                if not args.output:
                    parser.error("docs --check needs --output")
                current = Path(args.output).read_text(encoding="utf-8") \
                    if Path(args.output).is_file() else None
                if current != text:
                    print(f"{args.output} is out of date; run: python3 tools/targets.py docs "
                          f"-o {args.output}", file=sys.stderr)
                    return 1
            else:
                _write(text, args.output)
        elif args.command == "check-docs":
            problems = check_docs(cfg, args.paths)
            for problem in problems:
                print(problem)
            if problems:
                print(f"{len(problems)} name(s) not in {Path(args.file).name}", file=sys.stderr)
                return 1
    except TargetsError as e:
        for problem in e.problems:
            print(problem, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
