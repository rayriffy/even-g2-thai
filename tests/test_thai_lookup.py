"""Exercise the new branch and stock continuation in the generated artifact."""
import struct
import unittest

from font_perf_fixture import FontFixture, LOOKUP


class ThaiLookupTests(unittest.TestCase):
    def setUp(self):
        self.f = FontFixture()

    def test_covered_thai_skips_native_callbacks_and_xip_guards(self):
        for runtime in (False, True):
            for size in self.f.fonts:
                root, _ = self.f.chain(size=size, runtime=runtime)
                result, raw = self.f.lookup(root, 0xE01)
                self.assertEqual(result, 1)
                self.assertEqual(raw[14:16], b'\x08\x00')
                self.assertEqual(struct.unpack_from('<I', raw, 24)[0], 0xE01)
        self.assertEqual(self.f.callbacks, [])
        self.assertEqual(self.f.guards, [])

    def test_stock_native_success_kerning_and_registers_are_preserved(self):
        root, _ = self.f.chain()
        self.f.native_result = True
        vm = self.f.vm
        regs = [getattr(vm.arm_const, f'UC_ARM_REG_R{i}') for i in range(4, 12)]
        for reg in regs:
            vm.uc.reg_write(reg, 0xC0FFEE00 + reg)
        result, raw = self.f.lookup(root, ord('A'), ord('V'))
        self.assertEqual(result, 1)
        self.assertEqual(struct.unpack_from('<I', raw)[0], root)
        self.assertEqual(struct.unpack_from('<H', raw, 4)[0], 17)
        self.assertEqual(self.f.callbacks[-1][2:], (ord('A'), ord('V')))
        self.assertEqual(len(self.f.guards), 2)
        for reg in regs:
            self.assertEqual(vm.uc.reg_read(reg), 0xC0FFEE00 + reg)
        self.assertEqual(vm.uc.reg_read(vm.arm_const.UC_ARM_REG_SP), 0x200FF000)
        vm.uc.mem_write(root + 20, b'\x04')  # stock kern-disabled flag
        self.f.lookup(root, ord('A'), ord('V'))
        self.assertEqual(self.f.callbacks[-1][3], 0)

    def test_missing_thai_and_unrelated_scripts_retain_stock_placeholders(self):
        root, native = self.f.chain()
        for cp in (0xE00, 0xE3B, 0xF704, 0x4E2D, 0xAC00, 0x1F600):
            before = len(self.f.callbacks)
            result, raw = self.f.lookup(root, cp)
            self.assertEqual(result, 0)
            self.assertEqual(raw[15] & 1, 1)
            self.assertEqual(len(self.f.callbacks) - before, len(native))

    def test_chain_without_thai_retains_native_thai_selection(self):
        root, _ = self.f.chain(with_thai=False)
        self.f.native_result = True
        result, raw = self.f.lookup(root, 0xE01)
        self.assertEqual(result, 1)
        self.assertEqual(struct.unpack_from('<I', raw)[0], root)
        self.assertEqual(len(self.f.callbacks), 1)

    def test_native_placeholder_retry_is_preserved(self):
        root, _ = self.f.chain(with_thai=False, count=2)
        self.f.native_result = self.f.native_placeholder = True
        result, raw = self.f.lookup(root, 0x4E2D)
        self.assertEqual(result, 1)
        self.assertEqual(struct.unpack_from('<I', raw)[0], root)
        self.assertEqual(len(self.f.callbacks), 3)

    def test_aligned_and_unaligned_descriptors_match_all_glyphs(self):
        for size, layout in self.f.fonts.items():
            # Use immutable fonts so descriptor pointers match across calls.
            for cp in list(range(0xE00, 0xE80)) + list(range(0xF700, 0xF704)):
                vm = self.f.vm
                before = vm.ram_next
                aligned = self.f.lookup(layout['address'], cp)
                for offset in (1, 2, 3):
                    self.assertEqual(self.f.lookup(layout['address'], cp, offset=offset),
                                     aligned, (size, hex(cp), offset))
                vm.ram_next = before

    def test_all_thai_descriptors_match_original_stock_dispatch(self):
        root, _ = self.f.chain(runtime=False)
        vm = self.f.vm
        patched = bytes(vm.uc.mem_read(LOOKUP, 4))
        for cp in list(range(0xE00, 0xE80)) + list(range(0xF700, 0xF704)):
            expected = self.f.lookup(root, cp)
            vm.uc.mem_write(LOOKUP, bytes.fromhex('2de9fe4f'))
            self.assertEqual(self.f.lookup(root, cp), expected)
            vm.uc.mem_write(LOOKUP, patched)


if __name__ == '__main__':
    unittest.main()
