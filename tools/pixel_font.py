#!/usr/bin/env python3
"""Rasterize pinned Maitree ExtraLight outlines on each native pixel grid."""
from functools import lru_cache
from collections import Counter
import argparse
import hashlib
import io
import json
from pathlib import Path
import PIL
from PIL import ImageFont, features
import fontTools
from fontTools.ttLib import TTFont
from font_blob import ALT_START, HEADER, MAGIC, SIZES, SIZE_RECORD, VALID_CODEPOINTS
from native_font_record import pack_record, RECORD_SIZE
from maitree_shaping import ALIASES, GLYPH_COUNT, NATIVE, record_index, rounded_units
from pixel_codec import encode_bitmap, encode_tiles, tiles

VERSION = 5
SOURCE = Path(__file__).resolve().parents[1] / "fonts/maitree/Maitree-ExtraLight.ttf"
SOURCE_SHA = "aaa310f9bc913882863b1d39bd70978b7d068ac831ef3789bd921f781392343d"
LINE_METRICS = ((25, 8), (31, 9), (37, 11), (43, 13),
                (49, 15), (56, 17), (61, 18), (73, 22))


@lru_cache(maxsize=8)
def native_font(size):
    # Memory-only cmap exposes existing GSUB glyphs. Outlines/hints stay intact.
    font = TTFont(SOURCE, recalcTimestamp=False)
    order = font.getGlyphOrder()
    for table in font["cmap"].tables:
        if table.isUnicode():
            table.cmap.update({0xD000 + gid: name for gid, name in enumerate(order)})
    data = io.BytesIO()
    font.save(data)
    data.seek(0)
    return ImageFont.truetype(data, size, layout_engine=ImageFont.Layout.BASIC)


@lru_cache(maxsize=2048)
def draw(codepoint, size_index):
    size = SIZES[size_index]
    font = native_font(size)
    dx = 0
    if codepoint == 0x0E33 or ALT_START + 26 <= codepoint <= ALT_START + 28:
        aa, advance = draw(0x0E32, size_index)
        if codepoint == ALT_START + 26:
            dot, _ = draw(ALT_START + 19, size_index)
        else:
            dot, _ = draw(0x0E4D, size_index)
            offset = -38 if codepoint == ALT_START + 27 else -17 if codepoint == ALT_START + 28 else 0
            dot = {(x + rounded_units(offset, size), y) for x, y in dot}
        return aa | dot, advance
    if codepoint >= ALT_START:
        glyph, dx = ALIASES[codepoint - ALT_START]
        if glyph == "blank":
            return set(), 0
        character = chr(0xD000 + glyph)
    else:
        character = chr(codepoint)
    mask, (left, top) = font.getmask2(character, mode="1", anchor="ls")
    width, height = mask.size
    data = bytes(mask)
    offset = rounded_units(dx, size)
    pixels = {(left + x + offset, top + y) for y in range(height) for x in range(width)
              if data[y * width + x]}
    if ALT_START + 35 <= codepoint <= ALT_START + 42:
        # Outward nikhahit+tone forms can overshoot the fixed stock ascent.
        # Move the intact mark only as far as needed; never clip its outline.
        ascent = LINE_METRICS[size_index][0] - LINE_METRICS[size_index][1]
        shift = max(0, -ascent - min(y for x, y in pixels))
        pixels = {(x, y + shift) for x, y in pixels}
    if ALT_START + 12 <= codepoint <= ALT_START + 20:
        # Mono grid fitting can put a narrow vowel on a tall consonant's stem.
        # Preserve the bitmap and adjust its attachment by the minimum pixel.
        body = set()
        for base in (0x0E1B, 0x0E1D, 0x0E1F):
            ink, advance = draw(base, size_index)
            body.update((x - advance, y) for x, y in ink)
        while pixels & body:
            pixels = {(x - 1, y) for x, y in pixels}
    if ALT_START + 8 <= codepoint <= ALT_START + 11:
        upper = set().union(*(draw(ALT_START + i, size_index)[0] for i in range(12, 21)))
        while pixels & upper:
            pixels = {(x, y - 1) for x, y in pixels}
    if ALT_START <= codepoint <= ALT_START + 3:
        upper = set().union(*(draw(cp, size_index)[0] for cp in (0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E4D)))
        while pixels & upper:
            pixels = {(x, y - 1) for x, y in pixels}
    if ALT_START + 21 <= codepoint <= ALT_START + 23:
        body = set()
        for base in (ALT_START + 44, ALT_START + 45):
            ink, advance = draw(base, size_index)
            body.update((x - advance, y) for x, y in ink)
        while pixels & body:
            pixels = {(x, y + 1) for x, y in pixels}
    return pixels, round(font.getlength(character))


def build_pixel_font(path=SOURCE):
    if path.resolve() != SOURCE.resolve() or hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Maitree ExtraLight source SHA-256 mismatch")
    if PIL.__version__ != "11.3.0":
        raise RuntimeError("Pillow 11.3.0 is required for reproducible native rasters")
    if features.version_module('freetype2') != '2.13.3' or fontTools.__version__ != '4.66.1':
        raise RuntimeError("native raster regeneration requires FreeType 2.13.3 and fontTools 4.66.1")
    records_offset = HEADER.size + len(SIZES) * SIZE_RECORD.size
    palette_offset = records_offset + len(SIZES) * GLYPH_COUNT * RECORD_SIZE
    output = bytearray(HEADER.pack(MAGIC, VERSION, len(SIZES), GLYPH_COUNT, RECORD_SIZE, records_offset))
    output.extend(b"".join(SIZE_RECORD.pack(size, *metrics, palette_offset)
                           for size, metrics in zip(SIZES, LINE_METRICS)))
    output.extend(bytes(len(SIZES) * GLYPH_COUNT * RECORD_SIZE))
    seen, report_rows = {}, []
    codepoints = [*NATIVE, *(ALT_START + i for i in range(len(ALIASES)))]
    rasters, frequency = {}, Counter()
    for size_index, size in enumerate(SIZES):
        line_height, baseline = LINE_METRICS[size_index]
        for cp in codepoints:
            pixels, advance = draw(cp, size_index)
            if pixels:
                left, right = min(x for x, y in pixels), max(x for x, y in pixels)
                top, bottom = min(y for x, y in pixels), max(y for x, y in pixels) + 1
            else:
                left, right, top, bottom = 0, 0, -1, 0
            if top < -(line_height - baseline) or bottom > baseline:
                raise ValueError(f"U+{cp:04X} {size}px exceeds stock line box: {top}..{bottom}")
            width, height = right - left + 1, bottom - top
            raster = bytes(255 if (left + x, top + y) in pixels else 0
                           for y in range(height) for x in range(width))
            patterns = tiles(raster, width, height)
            frequency.update(patterns)
            rasters[size_index, cp] = (pixels, advance, left, bottom, width, height, raster, patterns)
    palette = sorted(frequency, key=lambda tile: (-frequency[tile], tile))
    output.extend(len(palette).to_bytes(2, "little") + bytes(palette))
    for (size_index, cp), (pixels, advance, left, bottom, width, height, raster, patterns) in rasters.items():
        size = SIZES[size_index]
        encoded = encode_bitmap(raster, width, height)
        encoded = min(encoded, encode_tiles(patterns, palette), key=len)
        key = width, height, encoded
        if key not in seen:
            seen[key] = len(output)
            output.extend(encoded)
        offset = seen[key]
        if offset > 65535 or not -128 <= left <= 127 or not -128 <= -bottom <= 127:
            raise ValueError("font exceeds compact record bounds")
        index = record_index(cp)
        pack_record(output, records_offset + (size_index * GLYPH_COUNT + index) * RECORD_SIZE,
                                 offset, advance, width, height, left, -bottom)
        report_rows.append(dict(size=size, codepoint=f"U+{cp:04X}", width=width, height=height,
                                advance=advance, left=left, top=bottom-height, ink_pixels=len(pixels), codec=encoded[0]))
    report = dict(family="Maitree ExtraLight", weight=200, source_sha256=SOURCE_SHA,
                  font_sha256=hashlib.sha256(output).hexdigest(), font_bytes=len(output),
                  sizes=list(SIZES), covered_codepoints=len(VALID_CODEPOINTS),
                  contextual_glyphs=len(ALIASES), format="full-resolution A1; adaptive lossless rows",
                  rasterization="native monochrome FreeType; no erosion, thinning or resizing",
                  glyphs=report_rows)
    return bytes(output), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    blob, report = build_pixel_font(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "glyphs"}))


if __name__ == "__main__":
    main()
