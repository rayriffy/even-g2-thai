"""Device-path integration tests that execute the patched G2 main payload at
its real addresses under Unicorn emulation.

The first two hardware flashes booted and connected fine but crashed the lens
the moment any label was drawn: the letter-pair wrapper called a hardcoded
helper that dereferences its offset argument unconditionally, so the stock
NULL-offset lookahead faulted. These tests pin the corrected behavior against
the actual built artifact: the wrapper must route through the firmware's
decoder dispatch slot, tolerate NULL offsets, remap tone+SARA AM pairs to the
PUA alternates, and the glyph callbacks must rasterize every injected Thai
glyph without writing outside their buffers."""

from __future__ import annotations

import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from compact_font import COMPACT_RECORD, expand_blob
from pixel_codec import encode_bitmap
from native_font_record import glyph_record as compact_glyph_record
from maitree_shaping import shape_for_preview, ALT_COUNT, TAG_START, TAG_END, untag, adjustment, rounded_units
from render_preview import glyph_index
ARTIFACT = ROOT / "build" / "g2_2.4.0.24_thai.bin"
SPEC = ROOT / "patches" / "thai_patches.json"

LOAD = 0x437FE0
LETTER_HELPER_SITE = 0x0049F1E4
DECODE_SLOT_INDIRECT = 0x0049F554
STOCK_CHAIN_BUILD = 0x004758F0
LV_MALLOC = 0x00480876
RAM_BASE = 0x20000000
STACK_TOP = RAM_BASE + 0xFF000
EMU_DONE = 0x00080000

THAI_START = 0x0E00
ALT_START = 0xF700
THAI_RUNTIME_MAGIC = 0x43414854
RUNTIME_HEADER_BYTES = 80


def _main_payload(artifact: bytes) -> bytes:
    count = struct.unpack_from("<I", artifact, 8)[0]
    for index in range(count):
        offset, _size = struct.unpack_from("<II", artifact, 0x40 + index * 16 + 4)
        name = artifact[offset + 48 : offset + 128].split(b"\0")[0].decode()
        payload_size = struct.unpack_from("<I", artifact, offset + 8)[0]
        if name == "ota/s200_firmware_ota.bin":
            return artifact[offset + 128 : offset + 128 + payload_size]
    raise AssertionError("main payload not found in artifact")


class ThaiDevicePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import unicorn  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("unicorn not installed")
        if not ARTIFACT.exists():
            raise unittest.SkipTest("built Thai artifact absent")
        cls.payload = _main_payload(ARTIFACT.read_bytes())
        spec = json.loads(SPEC.read_text())
        metadata = spec["metadata"]
        cls.chain_wrapper_address = int(metadata["chain_wrapper_address"], 16)
        cls.font_blob_bytes = int(metadata["font_blob_bytes"])
        append = next(
            bytes.fromhex(patch["new"])
            for patch in spec["patches"]
            if patch["desc"].startswith("append Thai")
        )
        start = int(metadata["font_blob_offset_in_append"])
        cls.compact_blob = append[start : start + cls.font_blob_bytes]
        cls.font_blob = expand_blob(cls.compact_blob)
        font_blob_offset = cls.payload.find(cls.compact_blob)
        if font_blob_offset < 0 or cls.payload.find(cls.compact_blob, font_blob_offset + 1) >= 0:
            raise AssertionError("font blob must occur exactly once in the main payload")
        cls.font_blob_address = LOAD + font_blob_offset

    def setUp(self) -> None:
        import unicorn.arm_const as arm_const
        from unicorn import UC_ARCH_ARM, UC_MODE_THUMB, Uc
        from unicorn import UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE

        self.arm_const = arm_const
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.uc.mem_map(0x00100000, 0x01000000, UC_PROT_READ | UC_PROT_EXEC)
        self.uc.mem_write(LOAD, self.payload)
        self.uc.mem_map(RAM_BASE, 0x00100000, UC_PROT_READ | UC_PROT_WRITE | UC_PROT_EXEC)
        self.ram_next = RAM_BASE + 0x10000
        # One-instruction "bx lr" cache-flush stub in executable RAM.
        self.flush_stub = self.alloc(4)
        self.uc.mem_write(self.flush_stub, bytes.fromhex("7047"))

    def alloc(self, size: int) -> int:
        address = self.ram_next
        self.ram_next += (size + 3) & ~3
        return address

    def write_words(self, address: int, words: list[int]) -> None:
        self.uc.mem_write(address, struct.pack("<%dI" % len(words), *words))

    def read_word(self, address: int) -> int:
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def call(self, address: int, args: list[int]) -> int:
        for reg, value in zip(
            (
                self.arm_const.UC_ARM_REG_R0,
                self.arm_const.UC_ARM_REG_R1,
                self.arm_const.UC_ARM_REG_R2,
                self.arm_const.UC_ARM_REG_R3,
            ),
            args,
        ):
            self.uc.reg_write(reg, value)
        self.uc.reg_write(self.arm_const.UC_ARM_REG_SP, STACK_TOP)
        self.uc.reg_write(self.arm_const.UC_ARM_REG_LR, EMU_DONE)
        self.uc.emu_start(address | 1, EMU_DONE, timeout=5_000_000, count=1_000_000)
        return self.uc.reg_read(self.arm_const.UC_ARM_REG_R0)

    def decode_step(self, text_address: int, offset_value: int, use_offset_ptr=True):
        letter_ptr = self.alloc(8)
        next_ptr = self.alloc(8)
        offset_ptr = self.alloc(8) if use_offset_ptr else 0
        if use_offset_ptr:
            self.write_words(offset_ptr, [offset_value])
        self.write_words(letter_ptr, [0xDEAD])
        self.write_words(next_ptr, [0xDEAD])
        self.call(LETTER_HELPER_SITE, [text_address, letter_ptr, next_ptr, offset_ptr])
        result = [self.read_word(letter_ptr), self.read_word(next_ptr)]
        if use_offset_ptr:
            result.append(self.read_word(offset_ptr))
        return result

    def utf8(self, text: str) -> int:
        raw = text.encode("utf-8")
        address = self.alloc(len(raw) + 4)
        self.uc.mem_write(address, raw + b"\0\0\0\0")
        return address

    def font_arrays(self) -> dict[int, dict[str, int]]:
        """Locate the eight injected lv_font_t word blocks inside the payload by
        their pinned layout: {dsc|1, bitmap|1, 0, line_height, base_line, 0,
        0, 0, size_index}."""
        expected_heights = {16: (25, 8), 20: (31, 9), 24: (37, 11), 28: (43, 13),
                            32: (49, 15), 36: (56, 17), 40: (61, 18), 48: (73, 22)}
        found: dict[int, dict[str, int]] = {}
        for offset in range(0, len(self.payload) - 36, 4):
            words = struct.unpack_from("<9I", self.payload, offset)
            dsc, bitmap, zero, height, base, z1, z2, z3, index = words
            if zero or z1 or z2 or z3 or index > 7:
                continue
            if dsc & 1 != 1 or bitmap & 1 != 1 or dsc == bitmap:
                continue
            if height not in {v[0] for v in expected_heights.values()}:
                continue
            size = next(k for k, v in expected_heights.items() if v[0] == height)
            if expected_heights[size][1] != base:
                continue
            found.setdefault(
                size,
                {"address": LOAD + offset, "dsc": dsc & ~1, "bitmap": bitmap & ~1},
            )
        self.assertEqual(set(found), set(expected_heights))
        return found

    def glyph_record(self, size_index: int, codepoint: int) -> tuple[int, ...]:
        _, _, _, glyph_count, record_size, records_offset = struct.unpack_from(
            "<IHHHHI", self.font_blob
        )
        glyph_index = codepoint - THAI_START
        return struct.unpack_from(
            "<IHBBbbBB",
            self.font_blob,
            records_offset + (size_index * glyph_count + glyph_index) * record_size,
        )

    def runtime_font(self, layout: dict[str, int], slot_count: int = 4) -> tuple[int, int]:
        words = struct.unpack("<9I", self.uc.mem_read(layout["address"], 36))
        size_index = words[8]
        _, _, _, glyph_count, record_size, records_offset = struct.unpack_from(
            "<IHHHHI", self.font_blob
        )
        slot_bytes = 0
        for glyph_index in range(glyph_count):
            _, _, box_w, box_h, _, _, _, present = struct.unpack_from(
                "<IHBBbbBB",
                self.font_blob,
                records_offset + (size_index * glyph_count + glyph_index) * record_size,
            )
            if present:
                slot_bytes = max(slot_bytes, ((box_w + 3) & ~3) * box_h)
        runtime = self.alloc(RUNTIME_HEADER_BYTES + slot_count * slot_bytes)
        self.uc.mem_write(runtime, bytes(RUNTIME_HEADER_BYTES + slot_count * slot_bytes))
        self.uc.mem_write(runtime, struct.pack("<9I", *words))
        self.uc.mem_write(
            runtime + 36,
            struct.pack("<IIHBB", THAI_RUNTIME_MAGIC, 0, slot_bytes, slot_count, 0),
        )
        return runtime, slot_bytes

    def render_glyph(
        self, layout: dict[str, int], font_address: int, codepoint: int
    ) -> bytes:
        dsc_buffer = self.alloc(64)
        self.assertEqual(
            self.call(layout["dsc"], [font_address, dsc_buffer, codepoint, codepoint]),
            1,
        )
        box_w = struct.unpack_from("<H", self.uc.mem_read(dsc_buffer + 6, 2))[0]
        box_h = struct.unpack_from("<H", self.uc.mem_read(dsc_buffer + 8, 2))[0]
        stride = (box_w + 3) & ~3
        pixels = self.alloc(stride * box_h)
        self.uc.mem_write(pixels, bytes(stride * box_h))
        draw_desc = self.alloc(32)
        handler_table = self.alloc(32)
        slots = [0] * 8
        slots[4] = self.flush_stub | 1
        self.write_words(handler_table, slots)
        self.uc.mem_write(draw_desc + 8, struct.pack("<H", stride))
        self.uc.mem_write(draw_desc + 16, struct.pack("<I", pixels))
        self.uc.mem_write(draw_desc + 24, struct.pack("<I", handler_table))
        self.call(layout["bitmap"], [dsc_buffer, draw_desc])
        return b"".join(
            bytes(self.uc.mem_read(pixels + y * stride, box_w)) for y in range(box_h)
        )

    def stub_return(self, address: int, value: int) -> None:
        if address & 2:
            stub = bytes.fromhex("014870470000") + struct.pack("<I", value)
        else:
            stub = bytes.fromhex("00487047") + struct.pack("<I", value)
        self.uc.mem_write(address, stub)

    def test_decode_slot_matches_stock_dispatch(self) -> None:
        storage = self.read_word(DECODE_SLOT_INDIRECT)
        decoder = self.read_word(storage)
        self.assertEqual(storage, 0x007B9ED0)
        self.assertEqual(decoder, 0x0049F307)

    def test_ascii_decodes_through_hook(self) -> None:
        text = self.utf8("abc")
        self.assertEqual(self.decode_step(text, 0), [0x61, 0x62, 1])
        self.assertEqual(self.decode_step(text, 2), [0x63, 0, 3])

    def test_thai_tone_sara_am_pair_maps_to_alternate(self) -> None:
        text = self.utf8("น้ำ")
        # U+0E19 followed by U+0E49: no remap on the first pair.
        self.assertEqual(self.decode_step(text, 0), [0x0E19, 0x0E49, 3])
        # The tone mark before SARA AM must surface as its raised PUA form.
        self.assertEqual(self.decode_step(text, 3), [shape_for_preview("น้ำ")[1], 0x0E33, 6])
        # End of string: the decoder reports no letter and leaves the offset.
        self.assertEqual(self.decode_step(text, 9), [0, 0, 9])

    def test_tone_after_upper_vowel_maps_to_alternate(self) -> None:
        text = self.utf8("นี้")
        self.assertEqual(self.decode_step(text, 0), [0x0E19, 0x0E35, 3])
        self.assertEqual(self.decode_step(text, 3), [shape_for_preview("นี้")[1], 0x0E49, 6])
        self.assertEqual(self.decode_step(text, 6), [shape_for_preview("นี้")[2], 0, 9])

    def test_plain_tone_mark_without_sara_am_is_untouched(self) -> None:
        text = self.utf8("เก่ง")
        self.assertEqual(self.decode_step(text, 0), [0x0E40, 0x0E01, 3])
        # Mai ek before a consonant keeps its ordinary codepoint.
        self.assertEqual(self.decode_step(text, 6), [0x0E48, 0x0E07, 9])

    def test_null_offset_pointer_is_tolerated(self) -> None:
        text = self.utf8("abc")
        letter_ptr = self.alloc(8)
        next_ptr = self.alloc(8)
        self.write_words(letter_ptr, [0xDEAD])
        self.write_words(next_ptr, [0xDEAD])
        self.call(LETTER_HELPER_SITE, [text, letter_ptr, next_ptr, 0])
        self.assertEqual(self.read_word(letter_ptr), 0x61)
        self.assertEqual(self.read_word(next_ptr), 0x62)

    def test_every_glyph_rasterizes_within_bounds(self) -> None:
        fonts = self.font_arrays()
        for size, layout in sorted(fonts.items()):
            for codepoint in [*range(THAI_START, THAI_START + 0x80), *range(ALT_START, ALT_START + ALT_COUNT)]:
                with self.subTest(size=size, codepoint=hex(codepoint)):
                    saved_ram_next = self.ram_next
                    dsc_buffer = self.alloc(64)
                    status = self.call(
                        layout["dsc"],
                        [layout["address"], dsc_buffer, codepoint, codepoint],
                    )
                    if status == 0:
                        continue
                    box_w = struct.unpack_from("<H", self.uc.mem_read(dsc_buffer + 6, 2))[0]
                    box_h = struct.unpack_from("<H", self.uc.mem_read(dsc_buffer + 8, 2))[0]
                    self.assertGreater(box_w, 0)
                    _, _, size_count, glyph_count, _, records_offset = struct.unpack_from(
                        "<IHHHHI", self.font_blob
                    )
                    self.assertEqual(size_count, 8)
                    font_index = sorted(fonts).index(size)
                    record_offset = records_offset + (
                        font_index * glyph_count + glyph_index(codepoint)
                    ) * 12
                    bitmap_offset, _, _, _, _, _, row_bytes, _ = struct.unpack_from(
                        "<IHBBbbBB", self.font_blob, record_offset
                    )
                    for target_offset, stride in (
                        (0, (box_w + 3) & ~3),
                        (1, box_w if box_w & 1 else box_w + 1),
                    ):
                        with self.subTest(target_offset=target_offset, stride=stride):
                            pixels = self.alloc(target_offset + stride * box_h)
                            target = pixels + target_offset
                            guard_after = self.alloc(8)
                            sentinel = 0xA5A5A5A5
                            self.write_words(guard_after, [sentinel, sentinel])
                            draw_desc = self.alloc(32)
                            handler_table = self.alloc(32)
                            slots = [0] * 8
                            slots[4] = self.flush_stub | 1
                            self.write_words(handler_table, slots)
                            self.uc.mem_write(draw_desc + 8, struct.pack("<H", stride))
                            self.uc.mem_write(draw_desc + 16, struct.pack("<I", target))
                            self.uc.mem_write(draw_desc + 24, struct.pack("<I", handler_table))
                            self.call(layout["bitmap"], [dsc_buffer, draw_desc])
                            for y in range(box_h):
                                expected = bytearray()
                                row = self.font_blob[
                                    bitmap_offset + y * row_bytes : bitmap_offset + (y + 1) * row_bytes
                                ]
                                for packed in row:
                                    expected.extend(((packed >> 4) * 17, (packed & 0x0F) * 17))
                                self.assertEqual(
                                    self.uc.mem_read(target + y * stride, box_w),
                                    bytes(expected[:box_w]),
                                    f"size {size} codepoint {codepoint:#06x} A4 expansion drifted",
                                )
                            self.assertEqual(
                                self.read_word(guard_after),
                                sentinel,
                                f"size {size} codepoint {codepoint:#06x} overran its bitmap buffer",
                            )
                    self.ram_next = saved_ram_next

    def test_context_decoder_keeps_utf8_offsets_and_matches_all_reference_cases(self):
        reference = json.loads((ROOT / 'fonts/maitree/shaping-reference.json').read_text())
        for cases in reference['cases'].values():
            for text in cases:
                saved = self.ram_next
                address = self.utf8(text)
                raw = [ord(c) for c in text]
                expected = shape_for_preview(text)
                for i, cp in enumerate(expected):
                    following = raw[i + 1] if i + 1 < len(raw) else 0
                    self.assertEqual(self.decode_step(address, i * 3), [cp, following, (i + 1) * 3], text)
                self.assertEqual(bytes(self.uc.mem_read(address, len(text.encode()))), text.encode())
                self.ram_next = saved

    def test_context_tags_have_exact_metrics_and_pixels_in_final_firmware(self):
        reference = json.loads((ROOT / 'fonts/maitree/shaping-reference.json').read_text())
        tags = {cp for cases in reference['cases'].values() for text in cases
                for cp in shape_for_preview(text) if TAG_START <= cp < TAG_END}
        for size, layout in self.font_arrays().items():
            ix = (16, 20, 24, 28, 32, 36, 40, 48).index(size)
            for cp in tags:
                saved = self.ram_next
                canonical = untag(cp)
                _, advance, width, height, left, y = compact_glyph_record(self.compact_blob, ix, canonical)
                dsc = self.alloc(32)
                self.assertEqual(self.call(layout['dsc'], [layout['address'], dsc, cp, 0]), 1)
                dx, dy = adjustment(cp)
                expected = (advance, width, height, left + rounded_units(dx, size), y + rounded_units(dy, size))
                actual = struct.unpack('<HHHhh', self.uc.mem_read(dsc + 4, 10))
                self.assertEqual(actual, expected, (size, hex(cp)))
                self.assertEqual(self.render_glyph(layout, layout['address'], cp),
                                 self.render_glyph(layout, layout['address'], canonical))
                self.ram_next = saved

    def test_runtime_cache_hit_survives_erased_bitmap_source(self) -> None:
        layout = self.font_arrays()[28]
        runtime, _slot_bytes = self.runtime_font(layout)
        codepoint = 0x0E01
        first = self.render_glyph(layout, runtime, codepoint)
        self.assertTrue(any(first))
        bitmap_offset, _, box_w, box_h, _, _ = compact_glyph_record(self.compact_blob, 3, codepoint)
        self.uc.mem_write(
            self.font_blob_address + bitmap_offset,
            encode_bitmap(bytes(box_w * box_h), box_w, box_h),
        )
        second = self.render_glyph(layout, runtime, codepoint)
        self.assertEqual(second, first)
        cached = {self.read_word(runtime + 48 + slot * 8) for slot in range(4)}
        self.assertIn(codepoint, cached)
        self.assertEqual(self.uc.mem_read(runtime + 47, 1), b"\0")

    def test_built_chain_wrapper_creates_renderable_runtime_font(self) -> None:
        layout = self.font_arrays()[28]
        root = self.alloc(36)
        tail = self.alloc(36)
        root_words = [0] * 9
        root_words[3] = 43
        root_words[7] = tail
        self.write_words(root, root_words)
        self.write_words(tail, [0] * 9)
        chain = self.alloc(4)
        self.write_words(chain, [root])
        runtime = self.alloc(0x4000)
        self.stub_return(STOCK_CHAIN_BUILD, chain)
        self.stub_return(LV_MALLOC, runtime)
        self.assertEqual(self.call(self.chain_wrapper_address, [0, 0]), chain)
        self.assertEqual(self.read_word(tail + 28), runtime)
        self.assertEqual(self.read_word(runtime + 36), THAI_RUNTIME_MAGIC)
        rendered = self.render_glyph(layout, runtime, 0x0E01)
        self.assertTrue(any(rendered))

    def test_runtime_cache_evicts_least_recently_used_glyph(self) -> None:
        layout = self.font_arrays()[28]
        runtime, _slot_bytes = self.runtime_font(layout, slot_count=2)
        first, second, third = 0x0E01, 0x0E02, 0x0E04
        self.render_glyph(layout, runtime, first)
        self.render_glyph(layout, runtime, second)
        self.render_glyph(layout, runtime, first)
        self.render_glyph(layout, runtime, third)
        cached = {self.read_word(runtime + 48 + slot * 8) for slot in range(2)}
        self.assertEqual(cached, {first, third})

    def test_busy_runtime_falls_back_without_mutating_cache(self) -> None:
        layout = self.font_arrays()[28]
        runtime, _slot_bytes = self.runtime_font(layout)
        self.uc.mem_write(runtime + 47, b"\1")
        rendered = self.render_glyph(layout, runtime, 0x0E01)
        self.assertTrue(any(rendered))
        self.assertEqual(
            {self.read_word(runtime + 48 + slot * 8) for slot in range(4)},
            {0},
        )
        self.assertEqual(self.uc.mem_read(runtime + 47, 1), b"\1")


if __name__ == "__main__":
    unittest.main()
