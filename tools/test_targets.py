#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-2026 SMAROBIX GmbH
# SPDX-License-Identifier: Apache-2.0
"""Tests for tools/targets.py. Run: python3 tools/test_targets.py"""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import targets  # noqa: E402

REGISTRY = "ghcr.io/smarobix/smarobix-buildx-images"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = targets.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class RealFile(unittest.TestCase):
    """targets.yml as committed."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = targets.load()
        cls.by_id = {t["id"]: t for t in cls.cfg["targets"]}

    def test_every_family_is_used(self):
        self.assertEqual({t["family"] for t in self.cfg["targets"]}, set(targets.FAMILIES))

    def test_build_matrix(self):
        matrix = targets.build_matrix(self.cfg)["include"]
        names = [f"{e['image']}-{e['distro']}" for e in matrix]
        manual = [t["id"] for t in self.cfg["targets"] if t["published"] == "manual"]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(self.by_id) - set(manual))
        for e in matrix:
            self.assertTrue(e["platform"], e)
            self.assertTrue(e["runs_on"], e)
            if e["board_dir"] == "rpi":
                self.assertIn("SUITE=", e["build_args"])
                self.assertIn("PY_VER=", e["build_args"])
            if e["board_dir"] == "oesdk":
                for key in ("base_image", "sdk_release", "sdk_installer", "sdk_sha256",
                            "sdk_env_setup"):
                    self.assertTrue(e[key], (e, key))
                self.assertIn(e["base_image"], manual)

    def test_package_matrix(self):
        matrix = targets.package_matrix(self.cfg)["include"]
        with_deb = [t for t in self.cfg["targets"] if t["deb"]]
        self.assertEqual(len(matrix), len(with_deb))
        for e in matrix:
            self.assertIn(e["deb_arch"], ("arm64", "armhf"))
            self.assertNotIn(",", e["suggests"])
            self.assertNotIn("python3-pip", e["suggests"])

    def test_matrix_is_one_line_of_json(self):
        for job in ("build", "package"):
            code, out, _ = run("matrix", job)
            self.assertEqual(code, 0)
            self.assertEqual(out.count("\n"), 1)
            self.assertIn("include", json.loads(out))

    def test_one_rmw_everywhere(self):
        self.assertEqual({t["rmw"] for t in self.cfg["targets"]}, {"rmw_cyclonedds_cpp"})

    def test_oe_sdk_runs_on_the_host(self):
        for t in self.cfg["targets"]:
            self.assertEqual(t["platform"] is None, t["family"] == "oe-sdk", t["id"])

    def test_docs_list_every_tag(self):
        text = targets.render_docs(self.cfg)
        self.assertTrue(text.startswith("<!-- Generated from targets.yml"))
        for t in self.cfg["targets"]:
            self.assertIn(f"`{t['id']}`", text)

    def test_committed_docs_are_current(self):
        page = targets.ROOT / "docs" / "reference" / "targets.md"
        code, _, err = run("docs", "--check", "-o", str(page))
        self.assertEqual(code, 0, err)


def minimal():
    """A small valid targets file: one target of each shape."""
    deb = {"pkg": "rpi-trixie", "target": "Debian 13 (trixie), arm64",
           "depends_extra": "python3", "recommends": "python3-lxml",
           "suggests": "build-essential cmake"}
    base = {"board": "B", "boards": "Bs", "rmw": "rmw_cyclonedds_cpp", "tested": []}
    return {
        "repository": "smarobix/smarobix-buildx-images",
        "x-anything": {"ignored": True},
        "targets": [
            dict(base, id="k26-jazzy", image="k26", distro="jazzy", family="ubuntu-apt",
                 os={"name": "Ubuntu 24.04", "codename": "noble"}, arch="arm64",
                 platform="linux/arm64",
                 build={"dir": "k26", "dockerfile": "Dockerfile.jazzy",
                        "runs_on": ["self-hosted", "ARM64"]}),
            dict(base, id="rpi-arm64-trixie-jazzy", image="rpi-arm64-trixie", distro="jazzy",
                 family="debian", os={"name": "Debian 13", "codename": "trixie"},
                 arch="arm64", platform="linux/arm64",
                 build={"dir": "rpi", "dockerfile": "Dockerfile.jazzy",
                        "runs_on": ["self-hosted", "ARM64"],
                        "args": {"SUITE": "trixie", "PY_VER": "3.13"}},
                 deb=dict(deb)),
            dict(base, id="k26-yocto-jazzy", image="k26-yocto", distro="jazzy",
                 family="yocto-native", os={"name": "Yocto", "codename": "scarthgap"},
                 arch="arm64", platform="linux/arm64", published="manual", build=None,
                 tested=[{"board": "KV260", "date": "2026-09-13", "note": "ran"}]),
            dict(base, id="k26-oesdk-jazzy", image="k26-oesdk", distro="jazzy",
                 family="oe-sdk", os={"name": "Yocto", "codename": "scarthgap"},
                 arch="arm64", platform=None,
                 build={"dir": "oesdk", "dockerfile": "Dockerfile",
                        "runs_on": ["self-hosted", "ARM64"], "platform": "linux/arm64",
                        "sdk": {"base_image": "k26-yocto-jazzy", "release": "r",
                                "installer": "i.sh", "sha256": "0" * 64,
                                "env_setup": "environment-setup-x"}}),
        ],
    }


class Validation(unittest.TestCase):
    """Every rule fails loudly, and names the target."""

    def check(self, mutate, *expected):
        data = minimal()
        mutate(data)
        with self.assertRaises(targets.TargetsError) as cm:
            targets.validate(data, check_files=False)
        text = str(cm.exception)
        for e in expected:
            self.assertIn(e, text)

    def t(self, data, i):
        return data["targets"][i]

    def test_minimal_is_valid(self):
        cfg = targets.validate(minimal(), check_files=False)
        self.assertEqual(cfg["registry"], REGISTRY)
        self.assertEqual(len(targets.build_matrix(cfg)["include"]), 3)
        self.assertEqual(len(targets.package_matrix(cfg)["include"]), 1)
        oesdk = targets.build_matrix(cfg)["include"][2]
        self.assertEqual(oesdk["platform"], "linux/arm64")
        self.assertEqual(targets.build_matrix(cfg)["include"][1]["build_args"],
                         "SUITE=trixie\nPY_VER=3.13")

    def test_missing_key(self):
        self.check(lambda d: self.t(d, 0).pop("rmw"), "k26-jazzy: missing rmw")

    def test_unknown_key(self):
        self.check(lambda d: self.t(d, 0).update(colour="red"), "unknown key colour")

    def test_unknown_top_level_key(self):
        self.check(lambda d: d.update(extra=1), "unknown key extra")

    def test_duplicate_id(self):
        self.check(lambda d: d["targets"].append(copy.deepcopy(self.t(d, 0))), "duplicate id")

    def test_id_is_image_distro(self):
        self.check(lambda d: self.t(d, 0).update(id="k26-humble"), "id must be image-distro")

    def test_unknown_family(self):
        self.check(lambda d: self.t(d, 0).update(family="zynq"), "unknown family 'zynq'")

    def test_null_platform_only_for_oe_sdk(self):
        self.check(lambda d: self.t(d, 0).update(platform=None), "only an oe-sdk target")

    def test_oe_sdk_platform_must_be_null(self):
        self.check(lambda d: self.t(d, 3).update(platform="linux/arm64"), "must be null")

    def test_arch_matches_platform(self):
        self.check(lambda d: self.t(d, 0).update(arch="armhf"), "does not match platform")

    def test_deb_fields(self):
        self.check(lambda d: self.t(d, 1)["deb"].pop("suggests"), "deb: missing suggests")

    def test_suggests_is_space_separated(self):
        self.check(lambda d: self.t(d, 1)["deb"].update(suggests="a, b"), "space-separated")

    def test_deb_needs_a_build(self):
        self.check(lambda d: self.t(d, 2).update(deb=dict(self.t(d, 1)["deb"])),
                   "needs a build")

    def test_manual_needs_null_build(self):
        self.check(lambda d: self.t(d, 0).update(published="manual"), "needs build: null")

    def test_null_build_needs_manual(self):
        self.check(lambda d: self.t(d, 2).pop("published"), "needs published: manual")

    def test_unquoted_version_arg(self):
        self.check(lambda d: self.t(d, 1)["build"]["args"].update(PY_VER=3.1),
                   "PY_VER must be a quoted string")

    def test_suite_matches_codename(self):
        self.check(lambda d: self.t(d, 1)["build"]["args"].update(SUITE="bookworm"),
                   "SUITE must equal os.codename")

    def test_oe_sdk_needs_sdk(self):
        self.check(lambda d: self.t(d, 3)["build"].pop("sdk"), "sdk is required")

    def test_sdk_base_image_is_a_target(self):
        self.check(lambda d: self.t(d, 3)["build"]["sdk"].update(base_image="nope"),
                   "is not a target in this file")

    def test_bad_sha256(self):
        self.check(lambda d: self.t(d, 3)["build"]["sdk"].update(sha256="abc"), "sha256")

    def test_tested_date(self):
        self.check(lambda d: self.t(d, 2)["tested"][0].update(date="13.09.2026"),
                   "date must be YYYY-MM-DD")

    def test_every_problem_is_reported(self):
        def mutate(d):
            self.t(d, 0).update(family="zynq")
            self.t(d, 1).update(id="wrong")
        self.check(mutate, "unknown family", "id must be image-distro")

    def test_missing_dockerfile(self):
        with self.assertRaises(targets.TargetsError) as cm:
            targets.validate(minimal(), root=Path(tempfile.mkdtemp()), check_files=True)
        self.assertIn("dockerfiles/k26/Dockerfile.jazzy does not exist", str(cm.exception))

    def test_duplicate_yaml_key(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "targets.yml"
            path.write_text("repository: a/b\nrepository: c/d\ntargets: []\n")
            with self.assertRaises(targets.TargetsError) as cm:
                targets.load(path)
            self.assertIn("duplicate key 'repository'", str(cm.exception))


class CheckDocs(unittest.TestCase):
    def setUp(self):
        self.cfg = targets.validate(minimal(), check_files=False)
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def scan(self, text, name="page.md"):
        path = Path(self.dir.name) / name
        path.write_text(text, encoding="utf-8")
        return targets.check_docs(self.cfg, [self.dir.name])

    def test_known_names_pass(self):
        self.assertEqual(self.scan(
            f"docker pull {REGISTRY}:k26-jazzy\n"
            f"`{REGISTRY}:k26-yocto-jazzy`, and {REGISTRY}:k26-oesdk-jazzy.\n"
            f"cache-from: type=registry,ref={REGISTRY}:k26-jazzy-buildcache\n"
            "sudo apt install ./smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.deb\n"
            "https://github.com/x/releases/download/v1.1.0/"
            "smarobix-ros-jazzy-rpi-trixie_1.1.0_arm64.tar.gz\n"
            "| `smarobix-ros-jazzy-rpi-trixie` | arm64 |\n"), [])

    def test_version_placeholder_is_read_as_a_version(self):
        # The site build fills {{ version }} in; the name around it is still checked.
        self.assertEqual(self.scan(
            "wget .../v{{ version }}/smarobix-ros-jazzy-rpi-trixie_{{ version }}_arm64.deb\n"
            "sudo apt install ./smarobix-ros-jazzy-rpi-trixie_{{version}}_arm64.deb\n"), [])
        problems = self.scan(
            "smarobix-ros-jazzy-rpi-trixie_{{ version }}_armhf.deb\n"
            "smarobix-ros-jazzy-rpi-forky_{{ version }}_arm64.deb\n")
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("not built for 'armhf'", problems[0])
        self.assertIn("unknown package 'smarobix-ros-jazzy-rpi-forky'", problems[1])

    def test_placeholders_are_ignored(self):
        self.assertEqual(self.scan(
            f"{REGISTRY}:<tag> {REGISTRY}:${{TAG}} {REGISTRY}:rpi-* {REGISTRY}:k26-…\n"
            f"{REGISTRY}:$TAG\n"
            "smarobix-ros-<distro>-<pkg>_<version>_<arch>.deb smarobix-ros-*\n"
            "smarobix-ros-jazzy-pynq-v3.1.1_<version>_armhf.deb\n"), [])

    def test_unknown_names_fail_with_file_and_line(self):
        problems = self.scan(
            "ok\n"
            f"{REGISTRY}:k26-jazzy-develop\n"
            "smarobix-ros-jazzy-pynq-v3.1.1\n"
            "smarobix-ros-jazzy-rpi-trixie_1.1.0_armhf.deb\n"
            f"{REGISTRY}:k26-yocto-jazzy-buildcache\n")
        self.assertEqual(len(problems), 4, problems)
        self.assertTrue(problems[0].endswith("page.md:2: unknown image tag 'k26-jazzy-develop'"))
        self.assertIn("page.md:3: unknown package 'smarobix-ros-jazzy-pynq-v3.1.1'", problems[1])
        self.assertIn("page.md:4:", problems[2])
        self.assertIn("not built for 'armhf'", problems[2])
        # A hand-pushed image has no build cache.
        self.assertIn("page.md:5:", problems[3])

    def test_only_markdown_in_directories(self):
        self.assertEqual(self.scan(f"{REGISTRY}:nope\n", name="notes.txt"), [])

    def test_explicit_file_and_missing_path(self):
        path = Path(self.dir.name) / "notes.txt"
        path.write_text(f"{REGISTRY}:nope\n")
        self.assertEqual(len(targets.check_docs(self.cfg, [path])), 1)
        with self.assertRaises(targets.TargetsError):
            targets.check_docs(self.cfg, [Path(self.dir.name) / "missing.md"])


class SelectChanged(unittest.TestCase):
    """The build matrix narrows to the images a change actually affects."""

    def setUp(self):
        self.matrix = targets.build_matrix(targets.validate(minimal(), check_files=False))

    def images(self, *changed):
        narrowed = targets.select_changed(self.matrix, changed)
        return sorted(e["image"] for e in narrowed["include"])

    def test_a_shared_input_keeps_every_image(self):
        for shared in targets.SHARED_INPUTS:
            with self.subTest(shared=shared):
                self.assertEqual(self.images(shared),
                                 sorted(e["image"] for e in self.matrix["include"]))

    def test_a_dockerfile_keeps_only_its_own_directory(self):
        entry = self.matrix["include"][0]
        got = self.images(f"dockerfiles/{entry['board_dir']}/Dockerfile.{entry['distro']}")
        self.assertIn(entry["image"], got)
        for other in self.matrix["include"]:
            if other["board_dir"] != entry["board_dir"]:
                self.assertNotIn(other["image"], got)

    def test_unrelated_paths_leave_nothing_to_build(self):
        self.assertEqual(self.images("docs/index.md", "mkdocs.yml", "README.md"), [])

    def test_a_directory_prefix_is_not_enough(self):
        # dockerfiles/rpi-extra/ must not match the rpi entry.
        entry = self.matrix["include"][0]
        self.assertEqual(self.images(f"dockerfiles/{entry['board_dir']}-extra/Dockerfile"), [])

    def test_blank_lines_are_ignored(self):
        self.assertEqual(self.images("", "   ", "\n"), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
