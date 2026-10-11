"""Coverage and deterministic compact-font generation, including odd edges."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compact_font import COMPACT_RECORD, compact_blob, decode_pixels, expand_blob
from font_blob import HEADER, RECORD, THAI_COUNT, build_blob


class CompactFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, _ = build_blob(ROOT / "third_party/2005_iannnnnAMD.ttf", thin_edges=1)
        cls.compact = compact_blob(cls.original)
        cls.expanded = expand_blob(cls.compact)

    def test_current_spec_reproduces_from_pinned_font(self):
        spec = json.loads((ROOT / "patches/thai_patches.json").read_text())
        append = next(bytes.fromhex(p["new"]) for p in spec["patches"]
                      if p["desc"].startswith("append Thai"))
        offset = spec["metadata"]["font_blob_offset_in_append"]
        self.assertEqual(append[offset:], self.compact)
        self.assertLess(len(self.compact), 25000)

    def test_all_sizes_keep_coverage_advance_dimensions_and_base_positions(self):
        _, _, sizes, glyphs, _, offset = HEADER.unpack_from(self.original)
        for index in range(sizes * glyphs):
            old = RECORD.unpack_from(self.original, offset + index * 12)
            new = RECORD.unpack_from(self.expanded, offset + index * 12)
            with self.subTest(size=index // glyphs, glyph=index % glyphs):
                self.assertEqual(new[1:5], old[1:5])
                self.assertEqual(new[6:], old[6:])
                if index % glyphs < THAI_COUNT:
                    self.assertEqual(new[5], old[5])
                else:
                    self.assertGreaterEqual(new[5], old[5])
                if new[-1]:
                    record = COMPACT_RECORD.unpack_from(self.compact, offset + index * 8)
                    self.assertTrue(any(decode_pixels(self.compact, record)))

    def test_four_alphas_and_odd_dimensions_have_known_pixels(self):
        pixels = decode_pixels(bytes([0x1B, 0x20]), (0, 0, 5, 3, 0, 0))
        self.assertEqual(pixels, bytes([0, 0, 85, 85, 170,
                                       0, 0, 85, 85, 170,
                                       255, 255, 0, 0, 170]))

    def test_significant_source_strokes_survive_sampling(self):
        for index in range(8 * 132):
            old = RECORD.unpack_from(self.original, 80 + index * 12)
            if not old[-1]:
                continue
            source, _, width, height, _, _, stride, _ = old
            record = COMPACT_RECORD.unpack_from(self.compact, 80 + index * 8)
            pixels = decode_pixels(self.compact, record)
            for y in range(height):
                for x in range(width):
                    packed = self.original[source + y * stride + x // 2]
                    alpha = (packed & 15) if x & 1 else packed >> 4
                    if alpha >= 4:
                        self.assertGreaterEqual(pixels[y * width + x], 60,
                                                (index, x, y))

    def test_truncated_bitmap_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_pixels(bytes([0x1B]), (0, 0, 5, 3, 0, 0))


if __name__ == "__main__":
    unittest.main()
