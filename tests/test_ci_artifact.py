"""Archive drift and clean-runner preview regression controls."""
import hashlib
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_ci_artifact import artifact_paths, prepare_artifact, main


class CiArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec = json.loads((ROOT / "patches/thai_patches.json").read_text())
        self.paths = artifact_paths(self.spec)
        for path in (self.paths["firmware"], self.paths["rebase_json"], self.paths["rebase_doc"],
                     "patches/thai_patches.json", "fonts/maitree/OFL.txt"):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)

    def test_clean_runner_archive_has_current_image_evidence_and_preview(self):
        self.assertFalse((self.root / "build/thai-preview.png").exists())
        paths = prepare_artifact(self.root)
        self.assertEqual(paths["version"], self.spec["base"][3:-4])
        self.assertEqual(hashlib.sha256((self.root / paths["firmware"]).read_bytes()).hexdigest(), self.spec["output_sha256"])
        self.assertEqual(hashlib.sha256((self.root / "build/thai_font.bin").read_bytes()).hexdigest(), self.spec["metadata"]["font_blob_sha256"])
        with Image.open(self.root / "build/thai-preview.png") as preview:
            self.assertEqual(preview.format, "PNG")
            self.assertIsNotNone(preview.getbbox())

    def test_next_rebase_version_controls_every_versioned_archive_path(self):
        paths = artifact_paths({"base": "g2_9.8.7.6.bin"})
        self.assertEqual(paths, dict(version="9.8.7.6", firmware="build/g2_9.8.7.6_thai.bin",
                                    rebase_json="docs/rebases/9.8.7.6.json", rebase_doc="docs/rebases/9.8.7.6.md"))
        for bad in ("g2_../9.8.7.6.bin", "g2_9.8.7.6.bin\nextra=value", "other.bin"):
            with self.assertRaises(ValueError):
                artifact_paths({"base": bad})

    def test_changed_image_is_rejected_before_any_preview_is_written(self):
        path = self.root / self.paths["firmware"]
        image = bytearray(path.read_bytes())
        image[-1] ^= 1
        path.write_bytes(image)
        with self.assertRaisesRegex(ValueError, "firmware SHA-256"):
            prepare_artifact(self.root)
        self.assertFalse((self.root / "build/thai-preview.png").exists())

    def test_stale_rebase_evidence_is_rejected(self):
        path = self.root / self.paths["rebase_json"]
        record = json.loads(path.read_text())
        record["patched_sha256"] = "0" * 64
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "rebase evidence"):
            prepare_artifact(self.root)

    def test_workflow_uses_spec_outputs_for_hashing_and_upload(self):
        workflow = (ROOT / ".github/workflows/build.yml").read_text()
        self.assertIn("id: artifact", workflow)
        self.assertIn("python tools/prepare_ci_artifact.py", workflow)
        self.assertIn('sha256sum "${{ steps.artifact.outputs.firmware }}"', workflow)
        for key in ("version", "firmware", "rebase_json", "rebase_doc"):
            self.assertIn("${{ steps.artifact.outputs." + key + " }}", workflow)
        self.assertNotRegex(workflow, r"(?:g2[-_]|rebases/)[0-9]+(?:\.[0-9]+){3}")

    def test_cli_appends_resolved_paths_to_github_step_outputs(self):
        output = self.root / "github-output"
        output.write_text("prior=value\n")
        with patch("prepare_ci_artifact.prepare_artifact", return_value=self.paths), \
                patch.dict("os.environ", {"GITHUB_OUTPUT": str(output)}), redirect_stdout(io.StringIO()):
            main()
        contents = output.read_text()
        self.assertTrue(contents.startswith("prior=value\n"))
        outputs = dict(line.split("=", 1) for line in contents.splitlines())
        self.assertEqual({key: outputs[key] for key in self.paths}, self.paths)


if __name__ == "__main__":
    unittest.main()
