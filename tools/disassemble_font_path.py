#!/usr/bin/env python3
"""Emit bounded font-path disassembly from the exact authenticated stock OTA."""
import argparse
import hashlib
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from generate_patch import G2_FILE_DELTA, STOCK_SHA256

RANGES = (
    ('font-manager background chain call', 0x476200, 0x47621C),
    ('font-manager foreground chain call', 0x47625E, 0x47627A),
    ('stock chain builder entry', 0x4758F0, 0x47593A),
    ('allocator', 0x480876, 0x4808BA),
    ('letter-pair helper and NULL-safe decoder', 0x49F1E4, 0x49F438),
    ('XIP acquire and release guards', 0x47A9EE, 0x47AA1A),
    ('bitmap dispatch', 0x508AAA, 0x508AFC),
    ('glyph release', 0x508AFC, 0x508B58),
    ('glyph descriptor fallback dispatch', 0x508B58, 0x508C8C),
    ('OTA flag read', 0x44AC68, 0x44AC78),
    ('MRAM settings write', 0x483650, 0x483678),
    ('OTA flag write', 0x483708, 0x48380E),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, default=Path('.cache/g2_2.4.0.24.bin'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--section', choices=('font', 'text', 'integrity'), default='font')
    args = parser.parse_args()
    data = args.stock.read_bytes()
    if hashlib.sha256(data).hexdigest() != STOCK_SHA256:
        raise ValueError('stock firmware SHA-256 mismatch')
    disassembler = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    lines = [f'; Stock SHA-256: {STOCK_SHA256}',
             '; Thumb addresses are installed MRAM addresses, not OTA file offsets.']
    for name, start, end in RANGES:
        section = ('text' if name.startswith('letter-pair') else
                   'integrity' if name.startswith(('OTA ', 'MRAM ')) else 'font')
        if section != args.section:
            continue
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
