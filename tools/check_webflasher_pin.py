#!/usr/bin/env python3
"""Verify that the vendored WebFlasher Case-USB pin matches the built artifact.

The charging-case writer refuses any file whose whole-bundle or Apollo-main
digest differs from src/lib/localTempleFlashTargets.js. This check keeps that
pin in lockstep with build/g2_2.2.9.22_thai.bin so a rebuilt firmware can never
silently fall back to a stale pin."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "build" / "g2_2.2.9.22_thai.bin"
PIN = (
    ROOT
    / "third_party"
    / "evenRealities-webflasher"
    / "src"
    / "lib"
    / "localTempleFlashTargets.js"
)


def fail(message: str) -> int:
    print(f"webflasher pin check FAILED: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if not ARTIFACT.is_file():
        return fail(f"missing artifact {ARTIFACT}; run make build first")
    data = ARTIFACT.read_bytes()
    bundle_sha = hashlib.sha256(data).hexdigest()

    count = struct.unpack_from("<I", data, 8)[0]
    main_payload = None
    for index in range(count):
        offset, _size = struct.unpack_from("<II", data, 0x40 + index * 16 + 4)
        name = data[offset + 48 : offset + 128].split(b"\0")[0].decode()
        if name == "ota/s200_firmware_ota.bin":
            payload_size = struct.unpack_from("<I", data, offset + 8)[0]
            main_payload = data[offset + 128 : offset + 128 + payload_size]
            break
    if main_payload is None:
        return fail("main component ota/s200_firmware_ota.bin not found")
    main_sha = hashlib.sha256(main_payload).hexdigest()

    if not PIN.is_file():
        return fail(
            f"missing {PIN}; run 'make webflasher' to set up the vendored patch"
        )
    text = PIN.read_text()

    expected = {
        "imageSha256": bundle_sha,
        "mainSha256": main_sha,
        "mainBytes": str(len(main_payload)),
    }
    problems = []
    for key, value in expected.items():
        pattern = rf'{key}:\s*"?(?:0x)?([0-9a-fA-F"]+)'
        match = re.search(pattern, text)
        observed = match.group(1).strip('"').lower() if match else None
        if observed != value.lower():
            problems.append(f"{key}: artifact {value} != pin {observed}")

    spec_path = ROOT / "patches" / "thai_patches.json"
    spec_sha = json.loads(spec_path.read_text())["output_sha256"]
    if spec_sha != bundle_sha:
        problems.append(
            f"thai_patches.json output_sha256 {spec_sha} != artifact {bundle_sha}; "
            "run ./build_thai.sh --update-patches"
        )

    if problems:
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return fail("pin drift detected; update patches/webflasher_case_usb_thai.patch")

    print(f"webflasher pin matches artifact {bundle_sha}")
    print(f"  main payload {main_sha} ({len(main_payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
