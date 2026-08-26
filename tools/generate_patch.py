#!/usr/bin/env python3
"""Compile the Thai hook and emit a deterministic stock-to-Thai patch spec."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

STOCK_SHA256 = "a03fbea9f68a9de6bc271daabb9f3a41c59053d1086622c76a4e990f829cc561"
FONT_SHA256 = "688f2ef20776a1f0286bd73bef4dd5d5c76640f4a7c4f0ea5f7c1b8d87a969b7"
FONT_SOURCE_COMMIT = "vendored:third_party/2005_iannnnnAMD.ttf"
MAINAPP_SUFFIX = "ota/s200_firmware_ota.bin"
APP_LOAD_ADDR = 0x00438000
APP_PREAMBLE = 0x20
APP_MAX_END = 0x007F0000
G2_FILE_DELTA = 0x379BFE
FONT_DSC_MAGIC = 0xA11D0001
FONT_BITMAP_MAGIC = 0xA11D0002
FONT_DATA_MAGIC = 0xA11D0003
HOOK_SITES = {
    0x00471318: bytes.fromhex("ff f7 36 fb"),
    0x00471376: bytes.fromhex("ff f7 07 fb"),
}
TEXT_HELPER_SITE = (0x00491BA4, bytes.fromhex("2d e9 f0 41"))


def align_up(value: int, alignment: int = 4) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def mram_addr(payload_offset: int) -> int:
    return APP_LOAD_ADDR + payload_offset - APP_PREAMBLE


def encode_bl(pc: int, target: int) -> bytes:
    displacement = target - (pc + 4)
    if displacement & 1 or not -(1 << 24) <= displacement < (1 << 24):
        raise ValueError(f"invalid Thumb BL {pc:#x} -> {target:#x}")
    immediate = (displacement >> 1) & 0xFFFFFF
    sign = (immediate >> 23) & 1
    i1 = (immediate >> 22) & 1
    i2 = (immediate >> 21) & 1
    imm10 = (immediate >> 11) & 0x3FF
    imm11 = immediate & 0x7FF
    j1 = (~(i1 ^ sign)) & 1
    j2 = (~(i2 ^ sign)) & 1
    first = 0xF000 | (sign << 10) | imm10
    second = 0xD000 | (j1 << 13) | (j2 << 11) | imm11
    return struct.pack("<HH", first, second)


def encode_bw(pc: int, target: int) -> bytes:
    displacement = target - (pc + 4)
    if displacement & 1 or not -(1 << 24) <= displacement < (1 << 24):
        raise ValueError(f"invalid Thumb B.W {pc:#x} -> {target:#x}")
    immediate = (displacement >> 1) & 0xFFFFFF
    sign = (immediate >> 23) & 1
    i1 = (immediate >> 22) & 1
    i2 = (immediate >> 21) & 1
    imm10 = (immediate >> 11) & 0x3FF
    imm11 = immediate & 0x7FF
    j1 = (~(i1 ^ sign)) & 1
    j2 = (~(i2 ^ sign)) & 1
    first = 0xF000 | (sign << 10) | imm10
    second = 0x9000 | (j1 << 13) | (j2 << 11) | imm11
    return struct.pack("<HH", first, second)


def crc32c_msb(data: bytes) -> int:
    polynomial = 0x1EDC6F41
    table = []
    for byte in range(256):
        value = byte << 24
        for _ in range(8):
            value = (
                ((value << 1) ^ polynomial) & 0xFFFFFFFF
                if value & 0x80000000
                else (value << 1) & 0xFFFFFFFF
            )
        table.append(value)
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ table[((crc >> 24) ^ byte) & 0xFF]
    return crc


def mainapp(image: bytes) -> tuple[int, int, int]:
    count = struct.unpack_from("<I", image, 8)[0]
    for index in range(count):
        _, offset, _, _ = struct.unpack_from("<IIII", image, 0x40 + index * 16)
        payload_size = struct.unpack_from("<I", image, offset + 8)[0]
        name = image[offset + 48 : offset + 128].split(b"\0")[0].decode("latin1")
        if name.endswith(MAINAPP_SUFFIX):
            return index, offset, payload_size
    raise ValueError("main-app component not found")


def compile_hook(helper: Path, source: Path) -> dict[str, object]:
    process = subprocess.run(
        [sys.executable, str(helper), str(source), "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise RuntimeError(process.stderr or process.stdout)
    return json.loads(process.stdout)


def function_offset(build: dict[str, object], name: str) -> int:
    for function in build["functions"]:
        if function["name"] == name:
            return int(function["offset"])
    raise ValueError(f"compiled function missing: {name}")


def replace_words(blob: bytearray, old: int, new: int, expected: int) -> None:
    needle = struct.pack("<I", old)
    replacement = struct.pack("<I", new)
    offsets = []
    cursor = 0
    while True:
        offset = blob.find(needle, cursor)
        if offset < 0:
            break
        offsets.append(offset)
        cursor = offset + 4
    if len(offsets) != expected:
        raise ValueError(f"magic {old:#x}: expected {expected} occurrences, got {len(offsets)}")
    for offset in offsets:
        blob[offset : offset + 4] = replacement


def build_spec(stock: bytes, font_blob: bytes, build: dict[str, object]) -> dict[str, object]:
    if hashlib.sha256(stock).hexdigest() != STOCK_SHA256:
        raise ValueError("stock firmware SHA-256 mismatch")
    index, component_offset, old_size = mainapp(stock)
    if component_offset + 128 + old_size != len(stock):
        raise ValueError("main app is not the final component")

    code_offset = align_up(old_size)
    code_base = mram_addr(code_offset)
    code = bytearray.fromhex(build["text"])
    font_offset = align_up(code_offset + len(code))
    font_base = mram_addr(font_offset)

    dsc_address = code_base + function_offset(build, "thai_get_glyph_dsc") | 1
    bitmap_address = code_base + function_offset(build, "thai_get_glyph_bitmap") | 1
    chain_address = code_base + function_offset(build, "thai_chain_build")
    text_helper_address = code_base + function_offset(
        build, "thai_text_encoded_letter_next_2"
    )
    replace_words(code, FONT_DSC_MAGIC, dsc_address, 8)
    replace_words(code, FONT_BITMAP_MAGIC, bitmap_address, 8)
    replace_words(code, FONT_DATA_MAGIC, font_base, 1)

    new_size = font_offset + len(font_blob)
    programmed_end = mram_addr(new_size)
    if programmed_end > APP_MAX_END:
        raise ValueError(
            f"patched main app ends at {programmed_end:#x}, beyond {APP_MAX_END:#x}"
        )

    append = bytearray(new_size - old_size)
    append[code_offset - old_size : code_offset - old_size + len(code)] = code
    append[font_offset - old_size : font_offset - old_size + len(font_blob)] = font_blob

    data = bytearray(stock)
    operations: list[dict[str, object]] = []

    def record(offset: int, new: bytes, description: str) -> None:
        old = bytes(data[offset : offset + len(new)])
        if old == new:
            return
        operations.append(
            {"offset": offset, "old": old.hex(), "new": new.hex(), "desc": description}
        )
        data[offset : offset + len(new)] = new

    for address, expected in HOOK_SITES.items():
        offset = address - G2_FILE_DELTA
        actual = bytes(data[offset : offset + 4])
        if actual != expected:
            raise ValueError(
                f"hook {address:#x}: expected {expected.hex()}, got {actual.hex()}"
            )
        record(offset, encode_bl(address, chain_address), f"font chain -> Thai fallback at {address:#x}")

    text_site, text_expected = TEXT_HELPER_SITE
    text_offset = text_site - G2_FILE_DELTA
    text_actual = bytes(data[text_offset : text_offset + 4])
    if text_actual != text_expected:
        raise ValueError(
            f"text helper {text_site:#x}: expected {text_expected.hex()}, got {text_actual.hex()}"
        )
    record(
        text_offset,
        encode_bw(text_site, text_helper_address),
        "LVGL letter-pair decode -> Thai contextual mark wrapper",
    )

    payload_end = component_offset + 128 + old_size
    operations.append(
        {
            "offset": payload_end,
            "old": "",
            "new": append.hex(),
            "desc": "append Thai fallback code and local bitmap payload",
        }
    )
    data.extend(append)

    record(component_offset + 8, struct.pack("<I", new_size), "main-app payload size")
    record(0x40 + index * 16 + 8, struct.pack("<I", new_size + 128), "main-app TOC size")
    preamble = struct.unpack_from("<I", data, component_offset + 128)[0]
    record(
        component_offset + 128,
        struct.pack("<I", (preamble & 0xFF000000) | (new_size & 0xFFFFFF)),
        "main-app preamble length",
    )
    preamble_crc = zlib.crc32(
        data[component_offset + 136 : component_offset + 128 + new_size]
    ) & 0xFFFFFFFF
    record(component_offset + 132, struct.pack("<I", preamble_crc), "main-app preamble CRC-32")
    component_crc = crc32c_msb(data[component_offset + 128 : component_offset + 128 + new_size])
    record(0x40 + index * 16 + 12, struct.pack("<I", component_crc), "main-app TOC CRC-32C")
    record(component_offset + 12, struct.pack("<I", component_crc), "main-app subheader CRC-32C")

    return {
        "schema_version": 1,
        "base": "g2_2.2.9.22.bin",
        "base_sha256": STOCK_SHA256,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "metadata": {
            "target": "Even Realities G2 2.2.9.22",
            "component_count": struct.unpack_from("<I", stock, 8)[0],
            "lvgl": "9.3.0-dev",
            "hook_sites": [f"0x{address:08X}" for address in HOOK_SITES],
            "chain_wrapper_address": f"0x{chain_address:08X}",
            "text_helper_hook_site": f"0x{text_site:08X}",
            "text_helper_wrapper_address": f"0x{text_helper_address:08X}",
            "code_bytes": len(code),
            "font_blob_offset_in_append": font_offset - old_size,
            "font_blob_bytes": len(font_blob),
            "font_blob_sha256": hashlib.sha256(font_blob).hexdigest(),
            "font_source_sha256": FONT_SHA256,
            "font_source_commit": FONT_SOURCE_COMMIT,
            "programmed_end": f"0x{programmed_end:08X}",
            "safe_ceiling": f"0x{APP_MAX_END:08X}",
        },
        "patches": operations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", required=True, type=Path)
    parser.add_argument("--font-blob", required=True, type=Path)
    parser.add_argument("--compiler-helper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(__file__).resolve().parents[1] / "patches" / "thai_font.c"
    build = compile_hook(args.compiler_helper, source)
    spec = build_spec(args.stock.read_bytes(), args.font_blob.read_bytes(), build)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(spec["metadata"], indent=2, sort_keys=True))
    print(f"output SHA-256 {spec['output_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
