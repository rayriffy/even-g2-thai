from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from apply_patches import apply_spec
from font_blob import (
    ALT_START,
    HEADER,
    MAGIC,
    RECORD,
    SIZE_RECORD,
    THAI_COUNT,
    TONE_MARKS,
    VALID_CODEPOINTS,
)
from generate_patch import encode_bl, encode_bw
from render_preview import shape_for_preview
from verify_firmware import verify


class ThaiPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads((ROOT / "patches/thai_patches.json").read_text())
        cls.append = next(
            bytes.fromhex(item["new"])
            for item in cls.spec["patches"]
            if item["desc"].startswith("append Thai")
        )
        meta = cls.spec["metadata"]
        offset = meta["font_blob_offset_in_append"]
        cls.font_blob = cls.append[offset : offset + meta["font_blob_bytes"]]

    def test_font_blob_identity_and_shape(self) -> None:
        meta = self.spec["metadata"]
        self.assertEqual(hashlib.sha256(self.font_blob).hexdigest(), meta["font_blob_sha256"])
        magic, version, sizes, glyphs, record_size, records_offset = HEADER.unpack_from(
            self.font_blob
        )
        self.assertEqual((magic, version, sizes, glyphs, record_size), (MAGIC, 2, 8, 132, RECORD.size))
        self.assertEqual(records_offset, HEADER.size + sizes * SIZE_RECORD.size)

    def test_expected_thai_coverage(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        for size_index in range(sizes):
            present = set()
            for glyph_index in range(THAI_COUNT):
                record = RECORD.unpack_from(
                    self.font_blob,
                    records_offset + (size_index * glyphs + glyph_index) * RECORD.size,
                )
                if record[-1]:
                    present.add(0x0E00 + glyph_index)
                    bitmap_offset, _, _, box_h, _, _, row_bytes, _ = record
                    self.assertLessEqual(bitmap_offset + box_h * row_bytes, len(self.font_blob))
            self.assertEqual(present, VALID_CODEPOINTS)

    def _glyph_pixels(self, record: tuple[int, ...]) -> set[tuple[int, int]]:
        bitmap_offset, _, box_w, box_h, ofs_x, ofs_y, row_bytes, present = record
        self.assertEqual(present, 1)
        pixels = set()
        for y in range(box_h):
            for x in range(box_w):
                packed = self.font_blob[bitmap_offset + y * row_bytes + x // 2]
                alpha = packed & 0x0F if x & 1 else packed >> 4
                if alpha >= 4:
                    pixels.add((ofs_x + x, -box_h - ofs_y + y))
        return pixels

    def test_sara_am_tone_alternates_do_not_overlap(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        for size_index in range(sizes):
            row = records_offset + size_index * glyphs * RECORD.size
            _, line_height, base_line, _ = SIZE_RECORD.unpack_from(
                self.font_blob, HEADER.size + size_index * SIZE_RECORD.size
            )
            sara_am = RECORD.unpack_from(
                self.font_blob, row + (0x0E33 - 0x0E00) * RECORD.size
            )
            sara_pixels = self._glyph_pixels(sara_am)
            for alternate_index, tone_mark in enumerate(TONE_MARKS):
                base = RECORD.unpack_from(
                    self.font_blob, row + (tone_mark - 0x0E00) * RECORD.size
                )
                alternate = RECORD.unpack_from(
                    self.font_blob,
                    row + (THAI_COUNT + alternate_index) * RECORD.size,
                )
                self.assertEqual(alternate[0], base[0])
                self.assertGreater(alternate[5], base[5])
                alternate_pixels = self._glyph_pixels(alternate)
                self.assertTrue(alternate_pixels.isdisjoint(sara_pixels))
                self.assertGreaterEqual(
                    min(y for _, y in alternate_pixels), -(line_height - base_line)
                )

    def test_sara_am_pair_maps_to_contextual_tone(self) -> None:
        shaped = shape_for_preview("น้ำ")
        self.assertEqual(shaped, [0x0E19, ALT_START + 1, 0x0E33])
        self.assertEqual(shape_for_preview("น้า"), [0x0E19, 0x0E49, 0x0E32])

    def test_combining_tone_mark_has_zero_advance(self) -> None:
        _, _, _, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        tone_index = 0x0E48 - 0x0E00
        record = RECORD.unpack_from(
            self.font_blob, records_offset + tone_index * RECORD.size
        )
        self.assertEqual(record[1], 0)

    def test_patch_has_two_font_chain_hooks(self) -> None:
        hooks = [item for item in self.spec["patches"] if item["desc"].startswith("font chain")]
        self.assertEqual(len(hooks), 2)
        self.assertEqual({item["old"] for item in hooks}, {"fff736fb", "fff707fb"})
        target = int(self.spec["metadata"]["chain_wrapper_address"], 16)
        for hook, address_text in zip(hooks, self.spec["metadata"]["hook_sites"]):
            address = int(address_text, 16)
            self.assertEqual(bytes.fromhex(hook["new"]), encode_bl(address, target))

    def test_patch_hooks_render_only_letter_pair_decoder(self) -> None:
        hook = next(
            item
            for item in self.spec["patches"]
            if item["desc"].startswith("LVGL letter-pair decode")
        )
        self.assertEqual(hook["old"], "2de9f041")
        site = int(self.spec["metadata"]["text_helper_hook_site"], 16)
        target = int(self.spec["metadata"]["text_helper_wrapper_address"], 16)
        self.assertEqual(bytes.fromhex(hook["new"]), encode_bw(site, target))

    def test_relocation_sentinels_are_absent(self) -> None:
        for sentinel in (0xA11D0001, 0xA11D0002, 0xA11D0003):
            self.assertNotIn(sentinel.to_bytes(4, "little"), self.append)

    def test_callback_pins_authenticated_iar_descriptor_layout(self) -> None:
        source = (ROOT / "patches/thai_font.c").read_text()
        self.assertIn("#define GLYPH_DSC_SIZE 32u", source)
        self.assertIn("#define GLYPH_DSC_FORMAT_OFFSET 14u", source)
        self.assertIn("#define GLYPH_DSC_GID_OFFSET 24u", source)
        self.assertIn("uint32_t *active_offset = offset ? offset : &local_offset;", source)

    def test_apply_and_verify_when_stock_is_cached(self) -> None:
        stock_path = ROOT / ".cache/g2_2.2.6.10.bin"
        if not stock_path.exists():
            self.skipTest("stock firmware cache absent")
        output = apply_spec(stock_path.read_bytes(), self.spec)
        self.assertEqual(hashlib.sha256(output).hexdigest(), self.spec["output_sha256"])
        self.assertEqual(len(verify(output)), 6)


if __name__ == "__main__":
    unittest.main()
