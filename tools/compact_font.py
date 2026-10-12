#!/usr/bin/env python3
"""Host font reader; legacy A2 conversion is retained for before/after evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from font_blob import HEADER, RECORD, SIZE_RECORD, THAI_COUNT, UPPER_MARKS
from pixel_codec import decode_rows, decode_native_bitmap
from maitree_shaping import ALIASES, NATIVE
from native_font_record import unpack_record

COMPACT_RECORD = struct.Struct("<HHBBbb")
COMPACT_VERSION = 3


def decode_pixels(blob: bytes, record: tuple[int, ...], version: int = COMPACT_VERSION) -> bytes:
    offset, _, width, height, _, _ = record
    if version == 4:
        return decode_rows(blob, offset, width, height)
    if version == 5:
        return decode_native_bitmap(blob, offset, width, height)
    samples_w, samples_h = (width + 1) // 2, (height + 1) // 2
    count = samples_w * samples_h
    if offset + (count + 3) // 4 > len(blob):
        raise ValueError("compact bitmap exceeds font blob")
    samples = bytes(((blob[offset + i // 4] >> (6 - 2 * (i % 4))) & 3) * 85
                    for i in range(count))
    return bytes(samples[(y // 2) * samples_w + x // 2]
                 for y in range(height) for x in range(width))


def expand_blob(blob: bytes) -> bytes:
    """Host-only A4 view for previews and an independent emulator oracle."""
    magic, version, sizes, glyphs, record_size, offset = HEADER.unpack_from(blob)
    if version == 2:
        return blob
    if version not in (COMPACT_VERSION, 4, 5) or record_size != (6 if version == 5 else COMPACT_RECORD.size):
        raise ValueError("unsupported compact font format")
    result = bytearray(blob[:offset])
    expanded_count = THAI_COUNT + len(ALIASES) if version == 5 else glyphs
    HEADER.pack_into(result, 0, magic, 2, sizes, expanded_count, RECORD.size, offset)
    result.extend(bytes(sizes * expanded_count * RECORD.size))
    seen = {}
    for index in range(sizes * glyphs):
        record = (unpack_record(blob, offset + index * record_size) if version == 5
                  else COMPACT_RECORD.unpack_from(blob, offset + index * record_size))
        source, advance, width, height, x, y = record
        if not width:
            continue
        row_bytes = (width + 1) // 2
        if source not in seen:
            seen[source] = len(result)
            pixels = decode_pixels(blob, record, version)
            for row in range(height):
                for column in range(0, width, 2):
                    first = pixels[row * width + column] // 17
                    second = pixels[row * width + column + 1] // 17 if column + 1 < width else 0
                    result.append((first << 4) | second)
        size_index, glyph_index = divmod(index, glyphs)
        if version == 5:
            glyph_index = NATIVE[glyph_index] - 0x0E00 if glyph_index < len(NATIVE) else THAI_COUNT + glyph_index - len(NATIVE)
        output_index = size_index * expanded_count + glyph_index
        RECORD.pack_into(result, offset + output_index * RECORD.size,
                         seen[source], advance, width, height, x, y, row_bytes, 1)
    return bytes(result)


def compact_blob(blob: bytes) -> bytes:
    magic, version, sizes, glyphs, record_size, offset = HEADER.unpack_from(blob)
    if version != 2 or record_size != RECORD.size:
        raise ValueError("expected original A4 font")
    result = bytearray(blob[:offset])
    HEADER.pack_into(result, 0, magic, COMPACT_VERSION, sizes, glyphs, COMPACT_RECORD.size, offset)
    result.extend(bytes(sizes * glyphs * COMPACT_RECORD.size))
    seen = {}
    for index in range(sizes * glyphs):
        source, advance, width, height, x, y, row_bytes, present = RECORD.unpack_from(
            blob, offset + index * RECORD.size)
        if not present:
            continue
        if source not in seen:
            seen[source] = len(result)
            pixels = bytes(((blob[source + row * row_bytes + column // 2] >>
                            (0 if column & 1 else 4)) & 15) * 17
                           for row in range(height) for column in range(width))
            # Max pooling retains thin strokes and SARA AM's separate dot;
            # averaging erased that dot at the smallest sizes.
            samples = [max(pixels[(row + dy) * width + column + dx]
                           for dy in range(min(2, height - row))
                           for dx in range(min(2, width - column)))
                       for row in range(0, height, 2) for column in range(0, width, 2)]
            values = [(value * 3 + 127) // 255 for value in samples]
            if not any(values):
                raise ValueError(f"compact glyph {index} has no visible pixels")
            for start in range(0, len(values), 4):
                packed = 0
                for position, value in enumerate(values[start:start + 4]):
                    packed |= value << (6 - position * 2)
                result.append(packed)
        COMPACT_RECORD.pack_into(result, offset + index * COMPACT_RECORD.size,
                                 seen[source], advance, width, height, x, y)

    # Re-evaluate raised marks against the actual compact pixels, which can
    # grow by one pixel after nearest-neighbor expansion.
    for size in range(sizes):
        row = offset + size * glyphs * COMPACT_RECORD.size
        upper = set()
        for codepoint in {0x0E33, *UPPER_MARKS}:
            record = COMPACT_RECORD.unpack_from(result, row + (codepoint - 0x0E00) * 8)
            _, _, width, height, x, y = record
            pixels = decode_pixels(result, record)
            upper.update((x + i % width, -height - y + i // width)
                         for i, alpha in enumerate(pixels) if alpha >= 60)
        for alternate in range(4):
            address = row + (THAI_COUNT + alternate) * 8
            record = list(COMPACT_RECORD.unpack_from(result, address))
            pixels = decode_pixels(result, tuple(record))
            _, _, width, height, x, y = record
            while any((x + i % width, -height - y + i // width) in upper
                      for i, alpha in enumerate(pixels) if alpha >= 60):
                y += 1
            if y > 127:
                raise ValueError("compact alternate offset exceeds int8")
            record[5] = y
            COMPACT_RECORD.pack_into(result, address, *record)

        # The diagnostic raster line box must cover the raised alternates
        # after compact sampling. Stock font selection and advances stay fixed.
        target_size, line_height, baseline, _ = SIZE_RECORD.unpack_from(
            result, HEADER.size + size * SIZE_RECORD.size)
        ascent, descent = line_height - baseline, baseline
        for index in range(glyphs):
            record = COMPACT_RECORD.unpack_from(result, row + index * 8)
            _, _, width, height, _, y = record
            if not width:
                continue
            visible_y = [-height - y + i // width
                         for i, alpha in enumerate(decode_pixels(result, record)) if alpha >= 60]
            ascent = max(ascent, -min(visible_y))
            descent = max(descent, max(visible_y) + 1)
        SIZE_RECORD.pack_into(result, HEADER.size + size * SIZE_RECORD.size,
                              target_size, ascent + descent, descent, 0)
    return bytes(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.source.read_bytes()
    compact = compact_blob(source)
    args.output.write_bytes(compact)
    print(json.dumps({"source_bytes": len(source), "compact_bytes": len(compact),
                      "format": "half-resolution A2", "sizes": 8}))


if __name__ == "__main__":
    main()
