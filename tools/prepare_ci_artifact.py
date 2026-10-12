#!/usr/bin/env python3
"""Prepare verified archive inputs from the committed firmware patch version."""
import hashlib
import json
import os
from pathlib import Path
import re

from render_preview import render

ROOT = Path(__file__).resolve().parents[1]


def artifact_paths(spec):
    match = re.fullmatch(r"g2_([0-9]+(?:\.[0-9]+){3})\.bin", spec["base"])
    if not match:
        raise ValueError("invalid stock firmware filename in patch specification")
    version = match[1]
    return dict(version=version, firmware=f"build/g2_{version}_thai.bin",
                rebase_json=f"docs/rebases/{version}.json",
                rebase_doc=f"docs/rebases/{version}.md")


def prepare_artifact(root=ROOT):
    spec = json.loads((root / "patches/thai_patches.json").read_text())
    paths = artifact_paths(spec)
    image = (root / paths["firmware"]).read_bytes()
    if hashlib.sha256(image).hexdigest() != spec["output_sha256"]:
        raise ValueError("archive firmware SHA-256 differs from patch specification")
    record = json.loads((root / paths["rebase_json"]).read_text())
    if record["patched_sha256"] != spec["output_sha256"] or record["target_version"] != paths["version"]:
        raise ValueError("archive rebase evidence differs from firmware")
    for path in (paths["rebase_doc"], "fonts/maitree/OFL.txt"):
        if not (root / path).is_file():
            raise FileNotFoundError(f"missing archive input: {path}")

    append = next(p for p in spec["patches"] if p["desc"].startswith("append Thai"))
    payload = bytes.fromhex(append["new"])
    if image[append["offset"]:append["offset"] + len(payload)] != payload:
        raise ValueError("archive firmware does not contain its committed font payload")
    metadata = spec["metadata"]
    start, size = metadata["font_blob_offset_in_append"], metadata["font_blob_bytes"]
    if start < 0 or size <= 0 or start + size > len(payload):
        raise ValueError("invalid committed font payload bounds")
    font = payload[start:start + size]
    if hashlib.sha256(font).hexdigest() != metadata["font_blob_sha256"]:
        raise ValueError("committed font payload SHA-256 mismatch")
    # Normal builds apply the committed patch; they do not regenerate a TTF.
    # Produce the preview from those exact embedded pixels on a clean runner.
    preview = render(font)
    (root / "build/thai_font.bin").write_bytes(font)
    preview.save(root / "build/thai-preview.png")
    return paths


def main():
    paths = prepare_artifact()
    for key, value in paths.items():
        print(f"{key}={value}")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            for key, value in paths.items():
                stream.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
