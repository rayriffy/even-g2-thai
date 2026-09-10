"""Authenticate the 2.2.10.10 mapping and preserve all stock components."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from apply_patches import apply_spec
from generate_patch import APP_LOAD_ADDR, APP_PREAMBLE, G2_FILE_DELTA, mainapp


class RebaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stock = ROOT / ".cache/g2_2.2.10.10.bin"
        if not stock.exists():
            raise unittest.SkipTest("stock firmware cache absent")
        cls.stock = stock.read_bytes()
        cls.spec = json.loads((ROOT / "patches/thai_patches.json").read_text())
        cls.record = json.loads((ROOT / "docs/rebases/2.2.10.10.json").read_text())

    def test_component_mapping_is_derived_from_new_container(self):
        index, offset, size = mainapp(self.stock)
        self.assertEqual((index, offset, size), (5, 0xBE32D, 3713884))
        self.assertEqual(APP_LOAD_ADDR - offset - 128 - APP_PREAMBLE, G2_FILE_DELTA)
        self.assertIn(b"s200_v2.2.10.10", self.stock)
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
