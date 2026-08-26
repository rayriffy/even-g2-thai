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

    def test_sara_am_includes_nikhahit_above_sara_aa(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        sara_aa_index = 0x0E32 - 0x0E00
        sara_am_index = 0x0E33 - 0x0E00
        for size_index in range(sizes):
            row = records_offset + size_index * glyphs * RECORD.size
            sara_aa = RECORD.unpack_from(self.font_blob, row + sara_aa_index * RECORD.size)
            sara_am = RECORD.unpack_from(self.font_blob, row + sara_am_index * RECORD.size)
            sara_aa_pixels = self._glyph_pixels(sara_aa)
            sara_am_pixels = self._glyph_pixels(sara_am)
            self.assertEqual(sara_am[1], sara_aa[1])
            self.assertLess(
                min(y for _, y in sara_am_pixels),
                min(y for _, y in sara_aa_pixels),
            )

    def test_combining_tone_mark_has_zero_advance(self) -> None:
        _, _, _, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        tone_index = 0x0E48 - 0x0E00
        record = RECORD.unpack_from(
            self.font_blob, records_offset + tone_index * RECORD.size
        )
        self.assertEqual(record[1], 0)

    def test_combining_marks_overlay_the_preceding_thai_cell(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        combining_marks = [0x0E31, *range(0x0E34, 0x0E3B), 0x0E47, *range(0x0E48, 0x0E4F)]
        base_index = 0x0E01 - 0x0E00
        for size_index in range(sizes):
            row = records_offset + size_index * glyphs * RECORD.size
            base = RECORD.unpack_from(self.font_blob, row + base_index * RECORD.size)
            for codepoint in combining_marks:
                record = RECORD.unpack_from(
                    self.font_blob,
                    row + (codepoint - 0x0E00) * RECORD.size,
                )
                self.assertEqual(record[1], 0)
                self.assertLessEqual(record[2], base[1])
                mark_left = base[1] + record[4]
                self.assertLess(mark_left, base[1])
                self.assertGreater(mark_left + record[2], 0)

    def test_thai_base_glyph_uses_at_least_half_the_target_height(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        target_sizes = (16, 20, 24, 28, 32, 36, 40, 48)
        self.assertEqual(sizes, len(target_sizes))
        base_index = 0x0E01 - 0x0E00
        for size_index, target_size in enumerate(target_sizes):
            row = records_offset + size_index * glyphs * RECORD.size
            record = RECORD.unpack_from(self.font_blob, row + base_index * RECORD.size)
            self.assertGreaterEqual(record[3], target_size // 2)

    def test_all_rasterized_glyphs_fit_their_declared_line_box(self) -> None:
        _, _, sizes, glyphs, _, records_offset = HEADER.unpack_from(self.font_blob)
        for size_index in range(sizes):
            _, line_height, base_line, _ = SIZE_RECORD.unpack_from(
                self.font_blob, HEADER.size + size_index * SIZE_RECORD.size
            )
            row = records_offset + size_index * glyphs * RECORD.size
            for glyph_index in range(glyphs):
                record = RECORD.unpack_from(self.font_blob, row + glyph_index * RECORD.size)
                if not record[-1]:
                    continue
                pixels = self._glyph_pixels(record)
                if not pixels:
                    continue
                ys = [y for _, y in pixels]
                self.assertGreaterEqual(min(ys), -(line_height - base_line))
                self.assertLess(max(ys), base_line)

    def test_patch_has_two_font_chain_hooks(self) -> None:
        hooks = [item for item in self.spec["patches"] if item["desc"].startswith("font chain")]
        self.assertEqual(len(hooks), 2)
        self.assertEqual({item["old"] for item in hooks}, {"fff736fb", "fff707fb"})
        self.assertEqual(
            self.spec["metadata"]["hook_sites"], ["0x00471318", "0x00471376"]
        )
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
        self.assertEqual(site, 0x00491BA4)
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
        self.assertIn("#define STOCK_CHAIN_BUILD_THUMB 0x00470989u", source)
        self.assertIn("#define STOCK_DECODE_SLOT_INDIRECT 0x00491F14u", source)
        self.assertNotIn("STOCK_UTF8_NEXT_THUMB", source)
        self.assertIn("uint32_t *active_offset = offset ? offset : &local_offset;", source)
        self.assertIn("next = decode(text + *active_offset, 0);", source)

    def test_chain_append_only_writes_writable_ram(self) -> None:
        source = (ROOT / "patches/thai_font.c").read_text()
        self.assertIn("#define WRITABLE_RAM_BASE 0x20000000u", source)
        self.assertIn("#define WRITABLE_RAM_END 0x20080000u", source)
        self.assertIn("if(!writable_ram_node(last)) return chain_ptr;", source)

    def test_chain_append_never_writes_through_thai_font(self) -> None:
        source = (ROOT / "patches/thai_font.c").read_text()
        self.assertIn("static int is_thai_font(const uint32_t *font)", source)
        for size in (16, 20, 24, 28, 32, 36, 40, 48):
            self.assertIn(f"font == thai_font_{size}", source)
        self.assertIn("void *thai_chain_append(void *chain_ptr)", source)
        self.assertIn("if(!root || is_thai_font(root)) return chain_ptr;", source)
        self.assertIn(
            "if(is_thai_font((const uint32_t *)(uintptr_t)next)) return chain_ptr;",
            source,
        )
        self.assertIn("return thai_chain_append(chain);", source)

    def test_stock_fetch_preserves_existing_rollback_file(self) -> None:
        source = (ROOT / "build_thai.sh").read_text()
        self.assertIn('refusing to overwrite unverified $label at $path', source)
        self.assertIn('mktemp "${path}.candidate.XXXXXX"', source)
        self.assertIn('--output "$candidate"', source)
        self.assertIn('ln "$candidate" "$path"', source)
        self.assertNotIn('mv "$candidate" "$path"', source)
        self.assertNotIn('--output "$path"', source)
        self.assertIn("877c8d9490db0d3717ca012dd0f54556af3701bd", source)
        self.assertIn("sed '/^?? \\.DS_Store$/d'", source)

    def test_apply_and_verify_when_stock_is_cached(self) -> None:
        self.assertEqual(self.spec["base"], "g2_2.2.9.22.bin")
        self.assertEqual(
            self.spec["base_sha256"],
            "a03fbea9f68a9de6bc271daabb9f3a41c59053d1086622c76a4e990f829cc561",
        )
        self.assertEqual(self.spec["metadata"]["target"], "Even Realities G2 2.2.9.22")
        stock_path = ROOT / ".cache/g2_2.2.9.22.bin"
        if not stock_path.exists():
            self.skipTest("stock firmware cache absent")
        output = apply_spec(stock_path.read_bytes(), self.spec)
        self.assertEqual(hashlib.sha256(output).hexdigest(), self.spec["output_sha256"])
        self.assertEqual(len(verify(output)), self.spec["metadata"]["component_count"])


if __name__ == "__main__":
    unittest.main()
