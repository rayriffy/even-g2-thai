"""Regression tests that execute the real compiled Thai chain hook under ARM
emulation. The dashboard crash was caused by thai_chain_build appending a Thai
font twice: the second pass stored a fallback pointer into the const Thai font
object in flash. These tests load the actual Thumb-2 blob produced by the
g2flash compiler helper into Unicorn with firmware-flash pages mapped
read-only, so any illegal store fails the test exactly like the device
HardFault, and assert the append is idempotent and cycle-safe."""

from __future__ import annotations

import importlib.util
import shutil
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G2FLASH = ROOT.parent / "g2flash"
SOURCE = ROOT / "patches" / "thai_font.c"
FONT_BLOB = ROOT / "build" / "thai_font.bin"

CODE_BASE = 0x007D0000
FLASH_BASE = 0x00400000
FLASH_SIZE = 0x00400000
STOCK_CHAIN_BUILD_THUMB = 0x00470989
LV_MALLOC_THUMB = 0x00458383
RAM_BASE = 0x20000000
RAM_SIZE = 0x00100000
WRITABLE_RAM_BASE = 0x20000000
WRITABLE_RAM_END = 0x20080000
STACK_TOP = RAM_BASE + RAM_SIZE - 4
EMU_DONE = 0x00100000
DUMMY_CONFIGS = RAM_BASE + 0x1000
TEST_FONT_DATA = RAM_BASE + 0x40000
FONT_DATA_MAGIC = 0xA11D0003
THAI_RUNTIME_MAGIC = 0x43414854


def _toolchain_available() -> str | None:
    if importlib.util.find_spec("unicorn") is None:
        return "unicorn not installed"
    if shutil.which("clang") is None:
        return "clang not installed"
    if not (G2FLASH / "patches" / "build.py").exists():
        return "g2flash helper absent"
    return ""


class ThaiChainEmulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reason = _toolchain_available()
        if reason:
            raise unittest.SkipTest(reason)
        sys.path.insert(0, str(G2FLASH / "patches"))
        import build as g2build

        cls.g2build = g2build
        blob, funcs, _rodata_len = g2build.compile_text(str(SOURCE))
        cls.font_blob = FONT_BLOB.read_bytes()
        patched_blob = bytes(blob)
        magic = struct.pack("<I", FONT_DATA_MAGIC)
        if patched_blob.count(magic) != 1:
            raise AssertionError("compiled blob must contain one font-data magic word")
        cls.blob = patched_blob.replace(magic, struct.pack("<I", TEST_FONT_DATA), 1)
        cls.functions = {name: offset for name, offset, _size in funcs}
        for required in ("thai_chain_build", "thai_chain_append"):
            if required not in cls.functions:
                raise AssertionError(f"compiled blob missing {required}")
        cls.fonts = cls._font_symbols(G2FLASH / "obj" / "thai_font.o")
        expected_fonts = [f"thai_font_{size}" for size in (16, 20, 24, 28, 32, 36, 40, 48)]
        missing = [name for name in expected_fonts if name not in cls.fonts]
        if missing:
            raise AssertionError(f"font symbols missing from object: {missing}")

    @classmethod
    def _font_symbols(cls, obj_path: Path) -> dict[str, int]:
        """Blob-relative addresses of the injected font objects, using the same
        .text-then-rodata layout rule as build.py compile_text."""
        d, secs = cls.g2build.parse_elf(str(obj_path))
        text = cls.g2build.section(secs, ".text")
        text_idx = secs.index(text)
        base = {text_idx: 0}
        cursor = text["size"]
        for index, sec in enumerate(secs):
            if index == text_idx or not cls.g2build._is_rodata(sec):
                continue
            align = max(sec["align"], 1)
            cursor = (cursor + align - 1) // align * align
            base[index] = cursor
            cursor += sec["size"]
        symtab = cls.g2build.section(secs, ".symtab")
        strtab = secs[symtab["link"]]
        symbols: dict[str, int] = {}
        for i in range(symtab["size"] // 16):
            st_name, st_value, _st_size, st_info, _other, st_shndx = struct.unpack_from(
                "<IIIBBH", d, symtab["offset"] + i * 16
            )
            name = d[strtab["offset"] + st_name :]
            name = name[: name.index(b"\0")].decode()
            if name.startswith("thai_font_") and st_info & 0xF == 1:
                symbols[name] = base[st_shndx] + st_value
        return symbols

    def setUp(self) -> None:
        from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
        from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1
        from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_SP

        self.UC_ARM_REG_R0 = UC_ARM_REG_R0
        self.UC_ARM_REG_R1 = UC_ARM_REG_R1
        self.UC_ARM_REG_LR = UC_ARM_REG_LR
        self.UC_ARM_REG_SP = UC_ARM_REG_SP
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        from unicorn import UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE

        self.uc.mem_map(FLASH_BASE, FLASH_SIZE, UC_PROT_READ | UC_PROT_EXEC)
        self.uc.mem_map(RAM_BASE, RAM_SIZE, UC_PROT_READ | UC_PROT_WRITE)
        self.uc.mem_write(CODE_BASE, self.blob)
        self.uc.mem_write(TEST_FONT_DATA, self.font_blob)
        self.ram_next = RAM_BASE + 0x2000
        self.set_stock_return(0)
        self.set_malloc_return(0)

    def font(self, name: str) -> int:
        return CODE_BASE + self.fonts[name]

    def set_stock_return(self, value: int) -> None:
        # The stock call site targets 0x00470989 with the Thumb bit set, so the
        # CPU fetches from the even address; the stub must live there.
        stub = bytes.fromhex("00487047") + struct.pack("<I", value)
        self.uc.mem_write(STOCK_CHAIN_BUILD_THUMB & ~1, stub)

    def set_malloc_return(self, value: int) -> None:
        # This stock entry is 2 mod 4. LDR literal aligns PC down to a word,
        # so use imm8=1 and place the value at entry+6 rather than immediately
        # after BX LR.
        stub = bytes.fromhex("014870470000") + struct.pack("<I", value)
        self.uc.mem_write(LV_MALLOC_THUMB & ~1, stub)

    def node(self, line_height: int = 0, fallback: int = 0) -> int:
        address = self.ram_next
        self.ram_next += 36
        words = [0] * 9
        words[3] = line_height
        words[7] = fallback
        self.uc.mem_write(address, struct.pack("<9I", *words))
        return address

    def link(self, source: int, target: int) -> None:
        self.uc.mem_write(source + 28, struct.pack("<I", target))

    def read_word(self, address: int) -> int:
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def chain_object(self, root: int) -> int:
        address = self.ram_next
        self.ram_next += 4
        self.uc.mem_write(address, struct.pack("<I", root))
        return address

    def call(self, function: str, configs: int = DUMMY_CONFIGS, count: int = 4) -> int:
        entry = CODE_BASE + self.functions[function]
        # Snapshot after every harness-side write so any later difference is a
        # store performed by the emulated firmware itself.
        self.flash_snapshot = bytes(self.uc.mem_read(FLASH_BASE, FLASH_SIZE))
        self.uc.reg_write(self.UC_ARM_REG_R0, configs)
        self.uc.reg_write(self.UC_ARM_REG_R1, count)
        self.uc.reg_write(self.UC_ARM_REG_SP, STACK_TOP)
        self.uc.reg_write(self.UC_ARM_REG_LR, EMU_DONE)
        self.uc.emu_start(entry | 1, EMU_DONE, timeout=5_000_000, count=200_000)
        return self.uc.reg_read(self.UC_ARM_REG_R0)

    def assert_flash_unmodified(self) -> None:
        self.assertEqual(bytes(self.flash_snapshot), bytes(self.uc.mem_read(FLASH_BASE, FLASH_SIZE)))

    def build_three_node_chain(self) -> tuple[int, int]:
        root = self.node(line_height=30)
        middle = self.node()
        tail = self.node()
        self.link(root, middle)
        self.link(middle, tail)
        return self.chain_object(root), tail

    def test_first_call_appends_matching_thai_font(self) -> None:
        chain, tail = self.build_three_node_chain()
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(tail + 28), self.font("thai_font_20"))

    def test_second_call_is_idempotent(self) -> None:
        chain, tail = self.build_three_node_chain()
        self.set_stock_return(chain)
        self.call("thai_chain_build")
        appended = self.read_word(tail + 28)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(tail + 28), appended)
        self.assertEqual(self.read_word(appended + 28), 0)
        self.assert_flash_unmodified()

    def test_runtime_cache_font_is_writable_and_idempotent(self) -> None:
        runtime = self.ram_next
        self.ram_next += 0x4000
        self.set_malloc_return(runtime)
        chain, tail = self.build_three_node_chain()
        self.set_stock_return(chain)
        self.call("thai_chain_build")
        appended = self.read_word(tail + 28)
        self.assertEqual(appended, runtime)
        self.assertEqual(self.read_word(runtime + 36), THAI_RUNTIME_MAGIC)
        self.assertEqual(
            bytes(self.uc.mem_read(runtime, 36)),
            bytes(self.uc.mem_read(self.font("thai_font_20"), 36)),
        )
        self.set_malloc_return(runtime + 0x2000)
        self.call("thai_chain_build")
        self.assertEqual(self.read_word(tail + 28), runtime)
        self.assertEqual(self.read_word(runtime + 28), 0)
        self.assert_flash_unmodified()

    def test_allocator_failure_preserves_const_fallback(self) -> None:
        chain, tail = self.build_three_node_chain()
        self.set_stock_return(chain)
        self.set_malloc_return(0)
        self.call("thai_chain_build")
        self.assertEqual(self.read_word(tail + 28), self.font("thai_font_20"))

    def test_allocator_outside_writable_ram_preserves_const_fallback(self) -> None:
        chain, tail = self.build_three_node_chain()
        self.set_stock_return(chain)
        self.set_malloc_return(FLASH_BASE + 0x2000)
        self.call("thai_chain_build")
        self.assertEqual(self.read_word(tail + 28), self.font("thai_font_20"))
        self.assert_flash_unmodified()

    def test_existing_thai_tail_is_left_alone(self) -> None:
        root = self.node(line_height=30)
        self.link(root, self.font("thai_font_24"))
        chain = self.chain_object(root)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(root + 28), self.font("thai_font_24"))
        self.assert_flash_unmodified()

    def test_thai_root_is_left_alone(self) -> None:
        chain = self.chain_object(self.font("thai_font_28"))
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assert_flash_unmodified()

    def test_cycle_is_left_alone(self) -> None:
        first = self.node(line_height=30)
        second = self.node()
        self.link(first, second)
        self.link(second, first)
        chain = self.chain_object(first)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(second + 28), first)
        self.assert_flash_unmodified()

    def test_depth_bound_leaves_long_chain_alone(self) -> None:
        nodes = [self.node(line_height=30)] + [self.node() for _ in range(12)]
        for source, target in zip(nodes, nodes[1:]):
            self.link(source, target)
        chain = self.chain_object(nodes[0])
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(nodes[-1] + 28), 0)
        self.assert_flash_unmodified()

    def test_null_root_returns_chain_unchanged(self) -> None:
        chain = self.chain_object(0)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assert_flash_unmodified()

    def test_null_stock_result_returns_null(self) -> None:
        self.set_stock_return(0)
        self.assertEqual(self.call("thai_chain_build"), 0)

    def test_flash_resident_tail_is_left_alone(self) -> None:
        root = self.node(line_height=30)
        tail = FLASH_BASE + 0x90000
        self.uc.mem_write(tail, struct.pack("<9I", *([0] * 9)))
        self.link(root, tail)
        chain = self.chain_object(root)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(tail + 28), 0)
        self.assert_flash_unmodified()

    def test_ram_tail_below_end_is_appended(self) -> None:
        root = self.node(line_height=30)
        tail = WRITABLE_RAM_END - 0x24
        self.uc.mem_write(tail, struct.pack("<9I", *([0] * 9)))
        self.link(root, tail)
        chain = self.chain_object(root)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(tail + 28), self.font("thai_font_20"))

    def test_ram_tail_at_end_bound_is_left_alone(self) -> None:
        root = self.node(line_height=30)
        tail = WRITABLE_RAM_END + 0x10
        self.uc.mem_write(tail, struct.pack("<9I", *([0] * 9)))
        self.link(root, tail)
        chain = self.chain_object(root)
        self.set_stock_return(chain)
        returned = self.call("thai_chain_build")
        self.assertEqual(returned, chain)
        self.assertEqual(self.read_word(tail + 28), 0)

    def test_append_matches_line_height_mapping(self) -> None:
        for line_height, expected in (
            (27, "thai_font_16"),
            (33, "thai_font_20"),
            (39, "thai_font_24"),
            (45, "thai_font_28"),
            (52, "thai_font_32"),
            (58, "thai_font_36"),
            (66, "thai_font_40"),
            (80, "thai_font_48"),
        ):
            with self.subTest(line_height=line_height):
                root = self.node(line_height=line_height)
                tail = self.node()
                self.link(root, tail)
                chain = self.chain_object(root)
                self.set_stock_return(chain)
                self.call("thai_chain_append", configs=chain, count=0)
                self.assertEqual(self.read_word(tail + 28), self.font(expected))


if __name__ == "__main__":
    unittest.main()
