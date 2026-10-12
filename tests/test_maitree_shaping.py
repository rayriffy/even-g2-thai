"""Independent HarfBuzz oracle for the finite firmware Thai shaping rules."""
import json
from pathlib import Path
import sys
import unittest
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from pixel_font import SOURCE, SOURCE_SHA
from maitree_shaping import ALIASES, ALT_START, TAG_START, TAG_END, adjustment, shape_for_preview, untag, rounded_units
from font_blob import SIZES


class MaitreeShapingTests(unittest.TestCase):
    def test_glyphs_and_grid_attachments_match_1936_harfbuzz_references(self):
        reference = json.loads((SOURCE.parent / 'shaping-reference.json').read_text())
        self.assertEqual(reference['source_sha256'], SOURCE_SHA)
        font = TTFont(SOURCE)
        cmap = font.getBestCmap()
        order = font.getGlyphOrder()

        def item(gid, dx=0, dy=0):
            return dict(g=gid, dx=dx, dy=dy, ax=font['hmtx'][order[gid]][0])

        def placements(items, size):
            # HarfBuzz reorders SARA AM's nikhahit before its tone. Our two
            # opaque, disjoint mark bitmaps share the same pen position, so
            # draw order cannot change their ink. Preserve absolute pen/advance.
            pen, result = 0, []
            for glyph in items:
                result.append((pen, glyph['g'], rounded_units(glyph['dx'], size),
                               rounded_units(glyph['dy'], size), glyph['ax']))
                pen += glyph['ax']
            return sorted(result)

        count = 0
        for cases in reference['cases'].values():
            for text, expected in cases.items():
                actual = []
                for selected in shape_for_preview(text):
                    cp = untag(selected) if TAG_START <= selected < TAG_END else selected
                    dx, dy = adjustment(selected)
                    if cp == 0x0E33 or ALT_START + 26 <= cp <= ALT_START + 28:
                        gid = 758 if cp == ALT_START + 26 else 745
                        offset = 53 if cp == ALT_START + 26 else -38 if cp == ALT_START + 27 else -17 if cp == ALT_START + 28 else 0
                        actual.extend((item(gid, offset), item(font.getGlyphID(cmap[0x0E32]))))
                    elif cp >= ALT_START:
                        gid, offset = ALIASES[cp - ALT_START]
                        if gid != 'blank':
                            actual.append(item(gid, offset + dx, dy))
                    else:
                        actual.append(item(font.getGlyphID(cmap[cp]), dx, dy))
                for size in SIZES:
                    self.assertEqual(placements(actual, size), placements(expected, size), (size, text))
                count += 1
        self.assertEqual(count, 1936)


if __name__ == '__main__':
    unittest.main()
