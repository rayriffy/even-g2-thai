"""Native Maitree shapes, attached Thai marks, and exact lossless storage."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
from PIL import ImageFont
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from font_blob import SIZES, VALID_CODEPOINTS, COMBINING_MARKS, ALT_START, HEADER
from pixel_font import SOURCE, SOURCE_SHA, build_pixel_font, draw, LINE_METRICS
from pixel_codec import (encode_bitmap, decode_bitmap, encode_rows, decode_rows,
                         encode_tiles, tiles, decode_native_bitmap)
from native_font_record import pack_record, unpack_record, glyph_record
from maitree_shaping import (NATIVE, ALIASES, GLYPH_COUNT, TAG_START, TAG_END,
                             adjustment, rounded_units, shape_for_preview, untag)


class PixelFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob, cls.report = build_pixel_font()

    def test_source_is_google_maitree_extralight_200(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA)
        font = TTFont(SOURCE)
        self.assertEqual(font['OS/2'].usWeightClass, 275)  # Original font metadata; Google CSS maps it to 200.
        self.assertEqual(json.loads((SOURCE.parent / 'source.json').read_text())['weight'], 200)
        self.assertEqual(ImageFont.truetype(str(SOURCE), 28).getname(), ('Maitree', 'ExtraLight'))
        self.assertTrue(VALID_CODEPOINTS <= font.getBestCmap().keys())

    def test_current_spec_reproduces_from_pinned_outlines(self):
        spec = json.loads((ROOT / 'patches/thai_patches.json').read_text())
        append = next(bytes.fromhex(p['new']) for p in spec['patches'] if p['desc'].startswith('append Thai'))
        self.assertEqual(append[spec['metadata']['font_blob_offset_in_append']:], self.blob)
        self.assertEqual(spec['metadata']['font_source_sha256'], SOURCE_SHA)
        self.assertEqual(HEADER.unpack_from(self.blob), (0x49414854, 5, 8, GLYPH_COUNT, 6, 80))
        self.assertLess(len(self.blob) + spec['metadata']['code_bytes'], 0x7FE000 - 0x7F5AAC)

    def test_body_forms_and_baseline_match_unmodified_native_font(self):
        # Independent positive reference: direct source TTF, no remapped cmap.
        for ix, size in enumerate(SIZES):
            font = ImageFont.truetype(str(SOURCE), size, layout_engine=ImageFont.Layout.BASIC)
            for cp in VALID_CODEPOINTS - COMBINING_MARKS - {0x0E33}:
                mask, (left, top) = font.getmask2(chr(cp), mode='1', anchor='ls')
                width, height = mask.size
                data = bytes(mask)
                expected = {(left + x, top + y) for y in range(height) for x in range(width) if data[y * width + x]}
                pixels, advance = draw(cp, ix)
                self.assertEqual(pixels, expected, (size, chr(cp)))
                self.assertEqual(advance, round(font.getlength(chr(cp))))

    def test_similar_consonants_remain_distinguishable_at_all_sizes(self):
        for ix, size in enumerate(SIZES):
            for a, b in ('กถ', 'ถภ', 'คฅ', 'ดต', 'บป', 'ผฝ', 'พฟ', 'ฎฏ', 'ขช', 'ทฑ'):
                self.assertNotEqual(draw(ord(a), ix)[0], draw(ord(b), ix)[0], (size, a, b))

    def test_every_native_and_contextual_glyph_round_trips(self):
        for ix, size in enumerate(SIZES):
            for cp in (*NATIVE, *(ALT_START + i for i in range(len(ALIASES)))):
                offset, advance, width, height, left, ofs_y = glyph_record(self.blob, ix, cp)
                pixels, expected_advance = draw(cp, ix)
                expected = bytes(255 if (left + x, -height - ofs_y + y) in pixels else 0
                                 for y in range(height) for x in range(width))
                self.assertEqual(decode_native_bitmap(self.blob, offset, width, height), expected)
                self.assertEqual(advance, expected_advance)

    def test_float_vowels_stacks_tall_stems_and_lower_tails_do_not_collide(self):
        bases = ''.join(chr(cp) for cp in range(0x0E01, 0x0E2F) if cp not in (0x0E24, 0x0E26))
        samples = [b + v + t for b in bases for v in 'ัิีึื' for t in '่้๊๋']
        samples += [b + v for b in bases for v in 'ฺุูำ']
        samples += ['น้ำ', 'เก่ง', 'ป้ำ', 'ฝ่ำ', 'ฟ้ำ', 'กิ์', 'ปิ์', 'กํ่', 'ก่ํ', 'ป่ํ']
        for ix, size in enumerate(SIZES):
            for text in samples:
                layers, pen = [], 0
                for cp in shape_for_preview(text):
                    canonical = untag(cp) if TAG_START <= cp < TAG_END else cp
                    pixels, advance = draw(canonical, ix)
                    dx, dy = adjustment(cp)
                    layer = {(x + pen + rounded_units(dx, size), y - rounded_units(dy, size)) for x, y in pixels}
                    for previous in layers:
                        self.assertTrue(layer.isdisjoint(previous), (size, text))
                    layers.append(layer)
                    pen += advance
                pixels = set().union(*layers)
                line, baseline = LINE_METRICS[ix]
                self.assertGreaterEqual(min(y for x, y in pixels), -(line - baseline), (size, text))
                self.assertLess(max(y for x, y in pixels), baseline, (size, text))

    def test_full_resolution_controls_keep_isolated_pixels_and_odd_edges(self):
        for width, height in ((1, 1), (5, 3), (9, 17), (17, 9), (33, 21)):
            pixels = bytes(255 if (x + 3 * y) % 7 == 0 else 0 for y in range(height) for x in range(width))
            packed = encode_bitmap(pixels, width, height)
            self.assertEqual(decode_bitmap(packed, 0, width, height), pixels)
            patterns = tiles(pixels, width, height)
            palette = list(dict.fromkeys(patterns))
            # Build a standalone palette/stream with the same header slot.
            blob = bytearray(24)
            struct.pack_into('<H', blob, 22, 24)
            blob.extend(len(palette).to_bytes(2, 'little') + bytes(palette))
            offset = len(blob)
            blob.extend(encode_tiles(patterns, palette))
            self.assertEqual(decode_native_bitmap(blob, offset, width, height), pixels)
        self.assertEqual(encode_rows(bytes([255, 0, 0, 0, 255] * 20), 5, 20), bytes([19, 0x88]))

    def test_six_byte_metrics_keep_signed_offsets_and_reject_overflow(self):
        for x, y in ((-32, -64), (-1, -1), (0, 0), (31, 63)):
            blob = bytearray(6)
            pack_record(blob, 0, 65535, 63, 63, 63, x, y)
            self.assertEqual(unpack_record(blob, 0), (65535, 63, 63, 63, x, y))
        with self.assertRaises(ValueError):
            pack_record(bytearray(6), 0, 65536, 1, 1, 1, 0, 0)

    def test_malformed_codecs_are_rejected(self):
        for data, width, height in ((b'\0', 9, 1), (b'\1\3\x80', 1, 3), (b'\2\0', 1, 1), (b'\7', 1, 1)):
            with self.assertRaises(ValueError):
                decode_bitmap(data, 0, width, height)
        with self.assertRaises(ValueError):
            encode_rows(bytes([85]), 1, 1)
        blob = bytearray(24)
        struct.pack_into('<H', blob, 22, 24)
        blob.extend(b'\1\0\x80')
        for data in (b'\3\xf0', b'\3\1', b'\3\x81\0', b'\3\0\xff'):
            with self.assertRaises(ValueError):
                decode_native_bitmap(blob + data, len(blob), 5, 3)


if __name__ == '__main__':
    unittest.main()
