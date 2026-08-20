#!/usr/bin/env python3
"""Apply a fail-closed g2-thai patch specification to the stock OTA."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def apply_spec(base: bytes, spec: dict[str, object]) -> bytes:
    actual_base = hashlib.sha256(base).hexdigest()
    if actual_base != spec["base_sha256"]:
        raise ValueError(
            f"base SHA-256 mismatch: expected {spec['base_sha256']}, got {actual_base}"
        )

    output = bytearray(base)
    for index, operation in enumerate(spec["patches"]):
        offset = int(operation["offset"])
        old = bytes.fromhex(operation["old"])
        new = bytes.fromhex(operation["new"])
        actual = bytes(output[offset : offset + len(old)])
        if actual != old:
            raise ValueError(
                f"patch {index} ({operation['desc']}) old-byte mismatch at {offset:#x}: "
                f"expected {old.hex()}, got {actual.hex()}"
            )
        if not old and offset != len(output):
            raise ValueError(f"append patch {index} is not at EOF")
        output[offset : offset + len(old)] = new

    actual_output = hashlib.sha256(output).hexdigest()
    if actual_output != spec["output_sha256"]:
        raise ValueError(
            f"output SHA-256 mismatch: expected {spec['output_sha256']}, got {actual_output}"
        )
    return bytes(output)


def main() -> int:
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} STOCK PATCH_SPEC OUTPUT", file=sys.stderr)
        return 2
    stock_path, spec_path, output_path = map(Path, sys.argv[1:])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    output = apply_spec(stock_path.read_bytes(), spec)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    print(f"applied {len(spec['patches'])} patches; SHA-256 {spec['output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

