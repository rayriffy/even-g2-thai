"""Exercise helper bootstrap with real local Git submodules, without a network."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIN = "877c8d9490db0d3717ca012dd0f54556af3701bd"


class BuildSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.checkout = Path(self.temp.name) / "checkout"
        self.checkout.mkdir()
        self.helper = self.checkout / "third_party/g2flash"
        self.env = dict(os.environ, GIT_ALLOW_PROTOCOL="file")
        self.env.pop("G2FLASH_ROOT", None)
        self.git(self.checkout, "init", "-q")
        shutil.copyfile(ROOT / "build_thai.sh", self.checkout / "build_thai.sh")
        shutil.copyfile(ROOT / ".gitmodules", self.checkout / ".gitmodules")
        self.git(self.checkout, "config", "-f", ".gitmodules",
                 "submodule.third_party/g2flash.url", str(ROOT / "third_party/g2flash"))
        self.git(self.checkout, "add", "build_thai.sh", ".gitmodules")
        self.git(self.checkout, "update-index", "--add", "--cacheinfo",
                 f"160000,{PIN},third_party/g2flash")
        self.commit(self.checkout)
        # Deliberately stop at stock verification, immediately after setup.
        # This known-invalid file prevents any download or firmware generation.
        stock = json.loads((ROOT / "patches/thai_patches.json").read_text())["base"]
        cache = self.checkout / ".cache"
        cache.mkdir()
        (cache / stock).write_bytes(b"invalid stock fixture; preserve this file")

    def git(self, repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], env=self.env,
                              check=True, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE).stdout.strip()

    def commit(self, repo):
        self.git(repo, "-c", "user.name=Build Setup Test",
                 "-c", "user.email=build-test@example.invalid",
                 "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                 "commit", "-qm", "fixture")

    def run_build(self, override=None):
        env = self.env.copy()
        if override is not None:
            env["G2FLASH_ROOT"] = str(override)
        return subprocess.run(["bash", str(self.checkout / "build_thai.sh")],
                              cwd=self.temp.name, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=30)

    def assert_setup_passed(self, result):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite unverified stock G2", result.stdout)

    def init_helper(self):
        self.git(self.checkout, "submodule", "update", "--init", "--",
                 "third_party/g2flash")

    def test_plain_checkout_bootstraps_pinned_helper_without_a_sibling(self):
        self.assertFalse((self.checkout.parent / "g2flash").exists())
        self.assertFalse(self.helper.exists())
        self.assert_setup_passed(self.run_build())
        self.assertEqual(self.git(self.helper, "rev-parse", "HEAD"), PIN)
        self.assertTrue((self.helper / "patches/build.py").is_file())
        self.assert_setup_passed(self.run_build())

    def test_existing_dirty_helper_is_preserved_and_rejected(self):
        self.init_helper()
        source = self.helper / "patches/build.py"
        changed = source.read_bytes() + b"\n# local change\n"
        source.write_bytes(changed)
        result = self.run_build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("g2flash has local source changes", result.stdout)
        self.assertEqual(source.read_bytes(), changed)
        self.assertEqual(self.git(self.helper, "rev-parse", "HEAD"), PIN)

    def test_existing_unreviewed_revision_is_preserved_and_rejected(self):
        self.init_helper()
        (self.helper / "README.md").write_text("unreviewed helper fixture\n")
        self.git(self.helper, "add", "README.md")
        self.commit(self.helper)
        unreviewed = self.git(self.helper, "rev-parse", "HEAD")
        self.assertNotEqual(unreviewed, PIN)
        result = self.run_build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("g2flash must be pinned to " + PIN, result.stdout)
        self.assertEqual(self.git(self.helper, "rev-parse", "HEAD"), unreviewed)

    def test_explicit_override_does_not_initialize_default_helper(self):
        self.assert_setup_passed(self.run_build(ROOT / "third_party/g2flash"))
        self.assertFalse(self.helper.exists())

    def test_missing_explicit_override_is_not_silently_replaced(self):
        missing = self.checkout.parent / "missing-helper"
        result = self.run_build(missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("g2flash not found at " + str(missing), result.stdout)
        self.assertFalse(self.helper.exists())


if __name__ == "__main__":
    unittest.main()
