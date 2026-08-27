#!/usr/bin/env python3
"""Render the exact unshaped LVGL fallback layout for offline visual review."""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from font_blob import (
    ALT_START,
    HEADER,
    RECORD,
    SIZE_RECORD,
    THAI_COUNT,
    THAI_START,
    VALID_CODEPOINTS,
)

SAMPLES = ("ภาษาไทย", "กรุงเทพมหานคร", "น้ำ", "นี้", "เก่ง")
UPPER_MARKS = frozenset([0x0E31, *range(0x0E34, 0x0E38), 0x0E47, 0x0E4C, 0x0E4D, 0x0E4E])


def glyph_index(codepoint: int) -> int | None:
    if THAI_START <= codepoint < THAI_START + THAI_COUNT:
        return codepoint - THAI_START
    if ALT_START <= codepoint < ALT_START + 4:
        return THAI_COUNT + codepoint - ALT_START
    return None


def shape_for_preview(text: str) -> list[int]:
    codepoints = [ord(char) for char in text]
    for index in range(len(codepoints)):
        current = codepoints[index]
        following = codepoints[index + 1] if index + 1 < len(codepoints) else 0
        previous = codepoints[index - 1] if index else 0
        if (
            0x0E48 <= current <= 0x0E4B
            and (following == 0x0E33 or previous in UPPER_MARKS)
        ):
            codepoints[index] = ALT_START + current - 0x0E48
    return codepoints


def render(blob: bytes, size_index: int = 3) -> Image.Image:
    _, _, size_count, glyph_count, _, records_offset = HEADER.unpack_from(blob)
    if not 0 <= size_index < size_count:
        raise ValueError("font size index out of range")
    _, line_height, base_line, _ = SIZE_RECORD.unpack_from(
        blob, HEADER.size + size_index * SIZE_RECORD.size
    )

    width = 360
    margin = 12
    image = Image.new("L", (width, margin * 2 + line_height * len(SAMPLES)), 0)
    for row_index, text in enumerate(SAMPLES):
        pen_x = margin
        line_top = margin + row_index * line_height
        for codepoint in shape_for_preview(text):
            index = glyph_index(codepoint)
            if index is None or index >= glyph_count:
                pen_x += line_height // 2
                continue
            record = RECORD.unpack_from(
                blob,
                records_offset
                + (size_index * glyph_count + index) * RECORD.size,
            )
            bitmap_offset, advance, box_w, box_h, ofs_x, ofs_y, row_bytes, present = record
            if present:
                y1 = line_top + (line_height - base_line) - box_h - ofs_y
                for y in range(box_h):
                    source = bitmap_offset + y * row_bytes
                    for x in range(box_w):
                        packed = blob[source + x // 2]
                        alpha = (packed & 0x0F) if x & 1 else (packed >> 4)
                        px, py = pen_x + ofs_x + x, y1 + y
                        if 0 <= px < image.width and 0 <= py < image.height:
                            image.putpixel((px, py), max(image.getpixel((px, py)), alpha * 17))
            pen_x += advance
    return image


def render_grid(blob: bytes, size_index: int = 3, columns: int = 10) -> Image.Image:
    _, _, size_count, glyph_count, _, records_offset = HEADER.unpack_from(blob)
    if not 0 <= size_index < size_count:
        raise ValueError("size index out of range")
    _, line_height, base_line, _ = SIZE_RECORD.unpack_from(
        blob, HEADER.size + size_index * SIZE_RECORD.size
    )
    codepoints = sorted(VALID_CODEPOINTS)
    cell_width = line_height * 2
    cell_height = line_height + 22
    rows = (len(codepoints) + columns - 1) // columns
    image = Image.new("L", (cell_width * columns, cell_height * rows), 0)
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.load_default()
    for item_index, codepoint in enumerate(codepoints):
        row, column = divmod(item_index, columns)
        left = column * cell_width
        top = row * cell_height
        draw.rectangle((left, top, left + cell_width - 1, top + cell_height - 1), outline=48)
        record = RECORD.unpack_from(
            blob,
            records_offset + (size_index * glyph_count + glyph_index(codepoint)) * RECORD.size,
        )
        bitmap_offset, _, box_w, box_h, ofs_x, ofs_y, row_bytes, present = record
        if present:
            y1 = top + (line_height - base_line) - box_h - ofs_y
            for y in range(box_h):
                source = bitmap_offset + y * row_bytes
                for x in range(box_w):
                    packed = blob[source + x // 2]
                    alpha = (packed & 0x0F) if x & 1 else (packed >> 4)
                    px, py = left + cell_width // 2 + ofs_x + x, y1 + y
                    if 0 <= px < image.width and 0 <= py < image.height:
                        image.putpixel((px, py), max(image.getpixel((px, py)), alpha * 17))
        draw.text((left + 2, top + cell_height - 16), f"U+{codepoint:04X}", fill=180, font=label_font)
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("font_blob", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--grid", action="store_true")
    args = parser.parse_args()
    image = render_grid(args.font_blob.read_bytes()) if args.grid else render(args.font_blob.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(f"wrote {args.output} ({image.width}x{image.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
