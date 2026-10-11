"""Authenticate the 2.3.2.14 mapping and preserve all stock components."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from apply_patches import apply_spec
from generate_patch import APP_LOAD_ADDR, APP_MAX_END, APP_PREAMBLE, G2_FILE_DELTA, mainapp, crc32c_msb, build_spec
from verify_firmware import verify


class RebaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stock = ROOT / ".cache/g2_2.3.2.14.bin"
        if not stock.exists():
            raise unittest.SkipTest("stock firmware cache absent")
        cls.stock = stock.read_bytes()
        cls.spec = json.loads((ROOT / "patches/thai_patches.json").read_text())
        cls.record = json.loads((ROOT / "docs/rebases/2.3.2.14.json").read_text())

    def test_component_mapping_is_derived_from_new_container(self):
        index, offset, size = mainapp(self.stock)
        self.assertEqual((index, offset, size), (5, 0xBE370, 3922636))
        self.assertEqual(APP_LOAD_ADDR - offset - 128 - APP_PREAMBLE, G2_FILE_DELTA)
        self.assertIn(b"s200_v2.3.2.14", self.stock)
        self.assertEqual(hashlib.sha256(self.stock).hexdigest(), self.record["stock_sha256"])
        self.assertEqual(len(self.stock), self.record["stock_size"])

    def test_only_main_component_changes(self):
        patched = apply_spec(self.stock, self.spec)
        self.assertEqual(hashlib.sha256(patched).hexdigest(), self.record["patched_sha256"])
        for index, expected in enumerate(self.record["stock_components"]):
            _, offset, size, _ = struct.unpack_from("<IIII", self.stock, 0x40 + index * 16)
            payload = self.stock[offset + 128:offset + size]
            name = self.stock[offset + 48:offset + 128].split(b"\0")[0].decode()
            self.assertEqual(name, expected["name"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected["sha256"])
            if index != 5:
                self.assertEqual(patched[offset:offset + size], self.stock[offset:offset + size])
                self.assertEqual(patched[0x40 + index * 16:0x50 + index * 16],
                                 self.stock[0x40 + index * 16:0x50 + index * 16])
        _, offset, _ = mainapp(patched)
        self.assertEqual(hashlib.sha256(patched[offset + 128:]).hexdigest(),
                         self.record["patched_main_sha256"])

    def test_recorded_stock_anchors_are_unique(self):
        for anchor in self.record["anchors"]:
            with self.subTest(role=anchor["role"]):
                needle = bytes.fromhex(anchor["bytes"])
                self.assertGreaterEqual(len(needle), 16)
                self.assertEqual(self.stock.count(needle), 1)
                address = int(anchor["new_address"], 16) + anchor["anchor_offset"]
                self.assertEqual(self.stock.find(needle), address - G2_FILE_DELTA)

    def test_mismatched_stock_is_rejected(self):
        altered = bytearray(self.stock)
        altered[-1] ^= 1
        with self.assertRaises(ValueError):
            apply_spec(bytes(altered), self.spec)

    def test_stock_main_changes_only_at_four_hooks_and_preamble(self):
        patched = apply_spec(self.stock, self.spec)
        _, offset, size = mainapp(self.stock)
        allowed = set(range(offset + 128, offset + 136))
        for address in (0x471BC8, 0x471C26, 0x493FC0, 0x4EB3EC):
            allowed.update(range(address - G2_FILE_DELTA, address - G2_FILE_DELTA + 4))
        changed = {i for i in range(offset + 128, offset + 128 + size)
                   if self.stock[i] != patched[i]}
        self.assertTrue(changed <= allowed, changed - allowed)

    def test_install_limit_and_settings_are_authenticated_stock_literals(self):
        self.assertEqual(APP_MAX_END, 0x7FE000)
        for literal, expected in ((0x44AE68, 0x7FE000), (0x481C68, 0x7FF000)):
            self.assertEqual(struct.unpack_from("<I", self.stock, literal - G2_FILE_DELTA)[0], expected)
        self.assertLess(int(self.spec["metadata"]["programmed_end"], 16), APP_MAX_END)

    def test_legacy_font_format_cannot_generate_the_new_callback(self):
        legacy_header = struct.pack("<IHHHHI", 0x49414854, 2, 8, 132, 12, 80)
        with self.assertRaisesRegex(ValueError, "compact A2"):
            build_spec(self.stock, legacy_header, {})

    def test_valid_checksums_do_not_allow_an_image_past_the_ota_flag(self):
        image = bytearray(self.stock)
        index, offset, old_size = mainapp(image)
        new_size = APP_MAX_END - APP_LOAD_ADDR + APP_PREAMBLE + 4
        image.extend(bytes(new_size - old_size))
        struct.pack_into("<I", image, offset + 8, new_size)
        struct.pack_into("<I", image, 0x40 + index * 16 + 8, new_size + 128)
        word = struct.unpack_from("<I", image, offset + 128)[0]
        struct.pack_into("<I", image, offset + 128, (word & 0xFF000000) | new_size)
        struct.pack_into("<I", image, offset + 132, zlib.crc32(image[offset + 136:]) & 0xFFFFFFFF)
        crc = crc32c_msb(image[offset + 128:])
        struct.pack_into("<I", image, offset + 12, crc)
        struct.pack_into("<I", image, 0x40 + index * 16 + 12, crc)
        with self.assertRaisesRegex(ValueError, "install boundary"):
            verify(image)
