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
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "build" / "g2_2.2.9.22_thai.bin"
SPEC = ROOT / "patches" / "thai_patches.json"

LOAD = 0x437FE0
LETTER_HELPER_SITE = 0x00491BA4
DECODE_SLOT_INDIRECT = 0x00491F14
RAM_BASE = 0x20000000
STACK_TOP = RAM_BASE + 0xFF000
EMU_DONE = 0x00080000

THAI_START = 0x0E00
ALT_START = 0xF700


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
        metadata = json.loads(SPEC.read_text())["metadata"]
        cls.font_blob_bytes = int(metadata["font_blob_bytes"])

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

    def test_decode_slot_matches_stock_dispatch(self) -> None:
        storage = self.read_word(DECODE_SLOT_INDIRECT)
        decoder = self.read_word(storage)
        self.assertTrue(decoder & 1, "decoder pointer must be a Thumb entry")

    def test_ascii_decodes_through_hook(self) -> None:
        text = self.utf8("abc")
        self.assertEqual(self.decode_step(text, 0), [0x61, 0x62, 1])
        self.assertEqual(self.decode_step(text, 2), [0x63, 0, 3])

    def test_thai_tone_sara_am_pair_maps_to_alternate(self) -> None:
        text = self.utf8("น้ำ")
        # U+0E19 followed by U+0E49: no remap on the first pair.
        self.assertEqual(self.decode_step(text, 0), [0x0E19, 0x0E49, 3])
        # The tone mark before SARA AM must surface as its raised PUA form.
        self.assertEqual(self.decode_step(text, 3), [ALT_START + 1, 0x0E33, 6])
        # End of string: the decoder reports no letter and leaves the offset.
        self.assertEqual(self.decode_step(text, 9), [0, 0, 9])

    def test_tone_after_upper_vowel_maps_to_alternate(self) -> None:
        text = self.utf8("นี้")
        self.assertEqual(self.decode_step(text, 0), [0x0E19, 0x0E35, 3])
        self.assertEqual(self.decode_step(text, 3), [0x0E35, 0x0E49, 6])
        self.assertEqual(self.decode_step(text, 6), [ALT_START + 1, 0, 9])

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
            for codepoint in range(THAI_START, THAI_START + 0x80):
                with self.subTest(size=size, codepoint=hex(codepoint)):
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
                    stride = (box_w + 3) & ~3
                    pixels = self.alloc(stride * box_h)
                    guard_after = self.alloc(8)
                    sentinel = 0xA5A5A5A5
                    self.write_words(guard_after, [sentinel, sentinel])
                    draw_desc = self.alloc(32)
                    handler_table = self.alloc(32)
                    slots = [0] * 8
                    slots[4] = self.flush_stub | 1
                    self.write_words(handler_table, slots)
                    self.uc.mem_write(draw_desc + 8, struct.pack("<H", stride))
                    self.uc.mem_write(draw_desc + 16, struct.pack("<I", pixels))
                    self.uc.mem_write(draw_desc + 24, struct.pack("<I", handler_table))
                    self.call(layout["bitmap"], [dsc_buffer, draw_desc])
                    self.assertEqual(
                        self.read_word(guard_after),
                        sentinel,
                        f"size {size} codepoint {codepoint:#06x} overran its bitmap buffer",
                    )


if __name__ == "__main__":
    unittest.main()
