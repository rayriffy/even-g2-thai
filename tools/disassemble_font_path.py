#!/usr/bin/env python3
"""Emit bounded font-path disassembly from the exact authenticated stock OTA."""
import argparse
import hashlib
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from generate_patch import G2_FILE_DELTA, STOCK_SHA256

RANGES = (
    ('font-manager background chain call', 0x4718F8, 0x471914),
    ('font-manager foreground chain call', 0x471956, 0x471972),
    ('XIP acquire and release guards', 0x4760EA, 0x476116),
    ('bitmap dispatch', 0x4E8CE2, 0x4E8D34),
    ('glyph release', 0x4E8D34, 0x4E8D90),
    ('glyph descriptor fallback dispatch', 0x4E8D90, 0x4E8EC4),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, default=Path('.cache/g2_2.2.10.10.bin'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.stock.read_bytes()
    if hashlib.sha256(data).hexdigest() != STOCK_SHA256:
        raise ValueError('stock firmware SHA-256 mismatch')
    disassembler = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    lines = [f'; Stock SHA-256: {STOCK_SHA256}',
             '; Thumb addresses are installed MRAM addresses, not OTA file offsets.']
    for name, start, end in RANGES:
        lines.append(f'\n; {name}')
        instructions = list(disassembler.disasm(data[start - G2_FILE_DELTA:
                                                     end - G2_FILE_DELTA], start))
        assert instructions and instructions[-1].address + instructions[-1].size == end
        for insn in instructions:
            lines.append(f'{insn.address:08x}  {insn.bytes.hex():10} '
                         f'{insn.mnemonic:8} {insn.op_str}')
    args.output.write_text('\n'.join(lines) + '\n')
    print(f'STOCK_FONT_DISASSEMBLY_OK: {args.output}')


if __name__ == '__main__':
    main()
