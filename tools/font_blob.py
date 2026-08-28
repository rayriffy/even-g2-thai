#!/usr/bin/env python3
"""Generate the compact A4 Thai font payload consumed by thai_font.c."""

from __future__ import annotations

import hashlib
import json
import argparse
import struct
import sys
from pathlib import Path

import PIL
from PIL import Image, ImageFont, features

MAGIC = 0x49414854  # "THAI" in little endian
VERSION = 2
PILLOW_VERSION = "11.3.0"
SIZES = (16, 20, 24, 28, 32, 36, 40, 48)
RASTER_SCALE = 2
THIN_SUPERSAMPLE = 4
THAI_START = 0x0E00
THAI_COUNT = 0x80
ALT_START = 0xF700
SARA_AA = 0x0E32
SARA_AM = 0x0E33
NIKHAHIT = 0x0E4D
TONE_MARKS = (0x0E48, 0x0E49, 0x0E4A, 0x0E4B)
COMBINING_MARKS = frozenset(
    [0x0E31, *range(0x0E34, 0x0E3B), 0x0E47, *range(0x0E48, 0x0E4F)]
)
UPPER_MARKS = frozenset([0x0E31, *range(0x0E34, 0x0E38), 0x0E47, 0x0E4C, 0x0E4D, 0x0E4E])
GLYPH_COUNT = THAI_COUNT + len(TONE_MARKS)
RECORD = struct.Struct("<IHBBbbBB")
HEADER = struct.Struct("<IHHHHI")
SIZE_RECORD = struct.Struct("<HHHH")
VALID_CODEPOINTS = frozenset(
    [*range(0x0E01, 0x0E3B), 0x0E3F, *range(0x0E40, 0x0E5C)]
)


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not features.check_feature("raqm"):
        raise RuntimeError("Pillow with Raqm is required to shape Thai combining marks")
    font = ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
    try:
        font.set_variation_by_name("Regular")
    except (AttributeError, OSError, ValueError):
        pass
    return font


def _shaped_combining_mark(
    font: ImageFont.FreeTypeFont, codepoint: int, base_cell: int
) -> tuple[bytes, int, int, int, int]:
    base_mask, (base_left, base_top) = font.getmask2("ก", mode="L", anchor="ls")
    pair_mask, (pair_left, pair_top) = font.getmask2(
        f"ก{chr(codepoint)}", mode="L", anchor="ls"
    )
    base_width, base_height = base_mask.size
    pair_width, pair_height = pair_mask.size
    left = min(base_left, pair_left)
    top = min(base_top, pair_top)
    right = max(base_left + base_width, pair_left + pair_width)
    bottom = max(base_top + base_height, pair_top + pair_height)
    width, height = right - left, bottom - top
    base_pixels = bytearray(width * height)
    pair_pixels = bytearray(width * height)

    for source, source_width, source_height, source_left, source_top, target in (
        (bytes(base_mask), base_width, base_height, base_left, base_top, base_pixels),
        (bytes(pair_mask), pair_width, pair_height, pair_left, pair_top, pair_pixels),
    ):
        for y in range(source_height):
            target_offset = (source_top - top + y) * width + source_left - left
            source_offset = y * source_width
            for x in range(source_width):
                target[target_offset + x] = max(target[target_offset + x], source[source_offset + x])

    mark_pixels = bytearray(
        max(0, pair_pixel - base_pixel)
        for base_pixel, pair_pixel in zip(base_pixels, pair_pixels)
    )
    visible = [index for index, value in enumerate(mark_pixels) if value]
    if not visible:
        raise ValueError(f"U+{codepoint:04X} has no shaped combining-mark pixels")
    min_x = min(index % width for index in visible)
    max_x = max(index % width for index in visible)
    min_y = min(index // width for index in visible)
    max_y = max(index // width for index in visible)
    mark_width, mark_height = max_x - min_x + 1, max_y - min_y + 1
    cropped = b"".join(
        mark_pixels[(min_y + y) * width + min_x : (min_y + y) * width + max_x + 1]
        for y in range(mark_height)
    )
    return (
        cropped,
        mark_width,
        mark_height,
        left + min_x - base_cell,
        top + min_y,
    )


def _synthetic_sara_am(
    font: ImageFont.FreeTypeFont, base_cell: int
) -> tuple[bytes, int, int, int, int, int]:
    nikhahit, nikhahit_width, nikhahit_height, nikhahit_left, nikhahit_top = (
        _shaped_combining_mark(font, NIKHAHIT, base_cell)
    )
    sara_aa, (sara_aa_left, sara_aa_top) = font.getmask2(
        chr(SARA_AA), mode="L", anchor="ls"
    )
    sara_aa_width, sara_aa_height = sara_aa.size
    left = min(nikhahit_left, sara_aa_left)
    top = min(nikhahit_top, sara_aa_top)
    right = max(nikhahit_left + nikhahit_width, sara_aa_left + sara_aa_width)
    bottom = max(nikhahit_top + nikhahit_height, sara_aa_top + sara_aa_height)
    width, height = right - left, bottom - top
    pixels = bytearray(width * height)
    for source, source_width, source_height, source_left, source_top in (
        (nikhahit, nikhahit_width, nikhahit_height, nikhahit_left, nikhahit_top),
        (bytes(sara_aa), sara_aa_width, sara_aa_height, sara_aa_left, sara_aa_top),
    ):
        for y in range(source_height):
            target_offset = (source_top - top + y) * width + source_left - left
            source_offset = y * source_width
            for x in range(source_width):
                pixels[target_offset + x] = max(
                    pixels[target_offset + x], source[source_offset + x]
                )
    return (
        bytes(pixels),
        width,
        height,
        left,
        top,
        round(font.getlength(chr(SARA_AA))),
    )


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


def _thin_mask(mask: object, width: int, height: int, edges: int) -> bytes:
    pixels = bytearray(bytes(mask))
    for _ in range(edges):
        source = pixels[:]
        for y in range(height):
            for x in range(width):
                index = y * width + x
                neighbors = [source[index]]
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        neighbor_x = x + dx
                        neighbor_y = y + dy
                        if 0 <= neighbor_x < width and 0 <= neighbor_y < height:
                            neighbors.append(source[neighbor_y * width + neighbor_x])
                        else:
                            neighbors.append(0)
                pixels[index] = min(neighbors)
    return bytes(pixels)


def _downsample_thin_raster(
    mask: bytes, width: int, height: int, left: int, top: int, advance: int, scale: int
) -> tuple[bytes, int, int, int, int, int]:
    if scale == 1:
        return mask, width, height, left, top, advance
    output_left = left // scale
    output_top = top // scale
    output_right = -(- (left + width) // scale)
    output_bottom = -(- (top + height) // scale)
    output_width = output_right - output_left
    output_height = output_bottom - output_top
    image = Image.frombytes("L", (width, height), mask)
    output = image.resize((output_width, output_height), Image.Resampling.LANCZOS)
    return (
        output.tobytes(),
        output_width,
        output_height,
        output_left,
        output_top,
        round(advance / scale),
    )


def build_blob(font_path: Path, thin_edges: int = 0) -> tuple[bytes, dict[str, object]]:
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
        thin_scale = THIN_SUPERSAMPLE if thin_edges else 1
        raster_size = size * RASTER_SCALE * thin_scale
        font = _font(font_path, raster_size)
        ascent, descent = font.getmetrics()
        ascent = round(ascent / thin_scale)
        descent = round(descent / thin_scale)
        base_cell = round(font.getlength("ก"))
        records: list[tuple[int, int, int, int, int, int, int, int]] = []
        rendered: dict[
            int, tuple[tuple[int, int, int, int, int, int, int, int], set[tuple[int, int]]]
        ] = {}
        line_pixels: set[tuple[int, int]] = set()

        for codepoint in range(THAI_START, THAI_START + THAI_COUNT):
            if codepoint not in VALID_CODEPOINTS:
                records.append((0, 0, 0, 0, 0, 0, 0, 0))
                continue

            if codepoint == SARA_AM:
                mask, width, height, left, top, advance = _synthetic_sara_am(
                    font, base_cell
                )
            elif codepoint in COMBINING_MARKS:
                mask, width, height, left, top = _shaped_combining_mark(
                    font, codepoint, base_cell
                )
                advance = 0
            else:
                mask, (left, top) = font.getmask2(chr(codepoint), mode="L", anchor="ls")
                width, height = mask.size
                advance = round(font.getlength(chr(codepoint)))
            if thin_edges:
                erosion_pixels = thin_edges * (THIN_SUPERSAMPLE // 2)
                while erosion_pixels:
                    candidate = _thin_mask(mask, width, height, erosion_pixels)
                    if any(candidate):
                        mask = candidate
                        break
                    erosion_pixels -= 1
                mask, width, height, left, top, advance = _downsample_thin_raster(
                    bytes(mask), width, height, left, top, advance, thin_scale
                )
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
            line_pixels.update(collision_pixels)
            bitmaps.append(packed)
            bitmap_offset += len(packed)

        upper_mark_pixels = set(rendered[SARA_AM][1])
        for codepoint in UPPER_MARKS:
            upper_mark_pixels.update(rendered[codepoint][1])
        size_shifts: dict[str, int] = {}
        for tone_mark in TONE_MARKS:
            base_record, tone_pixels = rendered[tone_mark]
            raise_by = 1
            while any((x, y - raise_by) in upper_mark_pixels for x, y in tone_pixels):
                raise_by += 1
            alternate = list(base_record)
            alternate[5] += raise_by
            if alternate[5] > 127:
                raise ValueError(f"U+{tone_mark:04X} {size}px raised ofs_y out of range")
            records.append(tuple(alternate))
            line_pixels.update((x, y - raise_by) for x, y in tone_pixels)
            size_shifts[f"U+{tone_mark:04X}"] = raise_by

        min_y = min(y for _, y in line_pixels)
        max_y = max(y for _, y in line_pixels)
        ascent = max(ascent, -min_y)
        descent = max(descent, max_y + 1)
        size_rows.append((size, ascent + descent, descent, 0))
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
        "thin_edges": thin_edges,
            "sizes": [
            {
                "target_pixel_size": row[0],
                "raster_pixel_size": row[0] * RASTER_SCALE,
                "line_height": row[1],
                "base_line": row[2],
            }
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
    parser = argparse.ArgumentParser()
    parser.add_argument("font", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--thin", type=int, default=0, choices=(0, 1, 2))
    args = parser.parse_args()
    blob, report = build_blob(args.font, thin_edges=args.thin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
