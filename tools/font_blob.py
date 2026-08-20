#!/usr/bin/env python3
"""Generate the compact A4 Thai font payload consumed by thai_font.c."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import PIL
from PIL import ImageFont

MAGIC = 0x49414854  # "THAI" in little endian
VERSION = 2
PILLOW_VERSION = "11.3.0"
SIZES = (16, 20, 24, 28, 32, 36, 40, 48)
THAI_START = 0x0E00
THAI_COUNT = 0x80
ALT_START = 0xF700
TONE_MARKS = (0x0E48, 0x0E49, 0x0E4A, 0x0E4B)
GLYPH_COUNT = THAI_COUNT + len(TONE_MARKS)
RECORD = struct.Struct("<IHBBbbBB")
HEADER = struct.Struct("<IHHHHI")
SIZE_RECORD = struct.Struct("<HHHH")
VALID_CODEPOINTS = frozenset(
    [*range(0x0E01, 0x0E3B), 0x0E3F, *range(0x0E40, 0x0E5C)]
)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size)
    try:
        font.set_variation_by_name("Regular")
    except (AttributeError, OSError, ValueError):
        pass
    return font


def _pack_a4(mask: object, width: int, height: int) -> tuple[bytes, int]:
    pixels = bytes(mask)
    row_bytes = (width + 1) // 2
    packed = bytearray(row_bytes * height)
    for y in range(height):
        for x in range(width):
            alpha = min(15, (pixels[y * width + x] + 8) // 17)
            index = y * row_bytes + x // 2
            if x & 1:
                packed[index] |= alpha
            else:
                packed[index] = alpha << 4
    return bytes(packed), row_bytes


def build_blob(font_path: Path) -> tuple[bytes, dict[str, object]]:
    if PIL.__version__ != PILLOW_VERSION:
        raise RuntimeError(
            f"Pillow {PILLOW_VERSION} is required for reproducible rasters; "
            f"found {PIL.__version__}"
        )
    size_rows: list[tuple[int, int, int, int]] = []
    all_records: list[list[tuple[int, int, int, int, int, int, int, int]]] = []
    bitmaps: list[bytes] = []
    raised_tone_shifts: dict[int, dict[str, int]] = {}

    records_offset = HEADER.size + SIZE_RECORD.size * len(SIZES)
    bitmap_offset = records_offset + RECORD.size * len(SIZES) * GLYPH_COUNT

    for size in SIZES:
        font = _font(font_path, size)
        ascent, descent = font.getmetrics()
        size_rows.append((size, ascent + descent, descent, 0))
        records: list[tuple[int, int, int, int, int, int, int, int]] = []
        rendered: dict[
            int, tuple[tuple[int, int, int, int, int, int, int, int], set[tuple[int, int]]]
        ] = {}

        for codepoint in range(THAI_START, THAI_START + THAI_COUNT):
            if codepoint not in VALID_CODEPOINTS:
                records.append((0, 0, 0, 0, 0, 0, 0, 0))
                continue

            char = chr(codepoint)
            mask, (left, top) = font.getmask2(char, mode="L", anchor="ls")
            width, height = mask.size
            advance = round(font.getlength(char))
            bottom = top + height
            packed, row_bytes = _pack_a4(mask, width, height)
            pixels = bytes(mask)
            collision_pixels = {
                (left + x, top + y)
                for y in range(height)
                for x in range(width)
                if pixels[y * width + x] >= 60
            }

            for label, value in {
                "advance": advance,
                "width": width,
                "height": height,
                "left": left,
                "ofs_y": -bottom,
                "row_bytes": row_bytes,
            }.items():
                lower, upper = (-128, 127) if label in {"left", "ofs_y"} else (0, 255)
                if not lower <= value <= upper:
                    raise ValueError(f"U+{codepoint:04X} {size}px {label}={value} out of range")

            record = (bitmap_offset, advance, width, height, left, -bottom, row_bytes, 1)
            records.append(record)
            rendered[codepoint] = (record, collision_pixels)
            bitmaps.append(packed)
            bitmap_offset += len(packed)

        sara_am_pixels = rendered[0x0E33][1]
        size_shifts: dict[str, int] = {}
        for tone_mark in TONE_MARKS:
            base_record, tone_pixels = rendered[tone_mark]
            raise_by = 0
            while any((x, y - raise_by) in sara_am_pixels for x, y in tone_pixels):
                raise_by += 1
            alternate = list(base_record)
            alternate[5] += raise_by
            if alternate[5] > 127:
                raise ValueError(f"U+{tone_mark:04X} {size}px raised ofs_y out of range")
            records.append(tuple(alternate))
            size_shifts[f"U+{tone_mark:04X}"] = raise_by

        raised_tone_shifts[size] = size_shifts
        all_records.append(records)

    output = bytearray(
        HEADER.pack(MAGIC, VERSION, len(SIZES), GLYPH_COUNT, RECORD.size, records_offset)
    )
    output.extend(b"".join(SIZE_RECORD.pack(*row) for row in size_rows))
    for records in all_records:
        output.extend(b"".join(RECORD.pack(*record) for record in records))
    output.extend(b"".join(bitmaps))

    report = {
        "schema_version": 2,
        "pillow_version": PIL.__version__,
        "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
        "blob_sha256": hashlib.sha256(output).hexdigest(),
        "blob_bytes": len(output),
        "sizes": [
            {"pixel_size": row[0], "line_height": row[1], "base_line": row[2]}
            for row in size_rows
        ],
        "covered_codepoints": len(VALID_CODEPOINTS),
        "contextual_alternates": len(TONE_MARKS),
        "alternate_range": "U+F700..U+F703",
        "raised_tone_shifts": raised_tone_shifts,
        "range": "U+0E00..U+0E7F",
        "bitmap_format": "packed A4, row aligned",
    }
    return bytes(output), report


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} FONT OUTPUT", file=sys.stderr)
        return 2
    font_path, output_path = map(Path, sys.argv[1:])
    blob, report = build_blob(font_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(blob)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
