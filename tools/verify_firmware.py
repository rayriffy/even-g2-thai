#!/usr/bin/env python3
"""Verify EVENOTA component bounds and checksums without touching hardware."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

from generate_patch import APP_LOAD_ADDR, APP_MAX_END, APP_PREAMBLE, crc32c_msb


def verify(image: bytes) -> list[str]:
    count = struct.unpack_from("<I", image, 8)[0]
    if not 1 <= count <= 16:
        raise ValueError(f"implausible component count {count}")
    names = []
    for index in range(count):
        _, offset, size, toc_crc = struct.unpack_from("<IIII", image, 0x40 + index * 16)
        payload_size, sub_crc = struct.unpack_from("<II", image, offset + 8)
        if size != payload_size + 128:
            raise ValueError(f"component {index} size mismatch")
        end = offset + 128 + payload_size
        if end > len(image):
            raise ValueError(f"component {index} exceeds file")
        payload = image[offset + 128 : end]
        actual_crc = crc32c_msb(payload)
        if actual_crc != toc_crc or actual_crc != sub_crc:
            raise ValueError(f"component {index} CRC-32C mismatch")
        name = image[offset + 48 : offset + 128].split(b"\0")[0].decode("latin1")
        names.append(name)
        if name.endswith("s200_firmware_ota.bin"):
            preamble_size, stored_crc = struct.unpack_from("<II", payload)
            if preamble_size & 0xFFFFFF != payload_size & 0xFFFFFF:
                raise ValueError("main-app preamble size mismatch")
            actual_preamble = zlib.crc32(payload[8:]) & 0xFFFFFFFF
            if actual_preamble != stored_crc:
                raise ValueError("main-app preamble CRC-32 mismatch")
            programmed_end = APP_LOAD_ADDR + payload_size - APP_PREAMBLE
            if programmed_end > APP_MAX_END:
                raise ValueError("main app exceeds conservative MRAM ceiling")
    return names


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} FIRMWARE", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    names = verify(path.read_bytes())
    print(f"verified {len(names)} EVENOTA components")
    for name in names:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

