#!/usr/bin/env python3
"""Emit bounded font-path disassembly from the exact authenticated stock OTA."""
import argparse
import hashlib
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from generate_patch import G2_FILE_DELTA, STOCK_SHA256

RANGES = (
    ('font-manager background chain call', 0x471BC4, 0x471BE0),
    ('font-manager foreground chain call', 0x471C22, 0x471C3E),
    ('stock chain builder entry', 0x471238, 0x471282),
    ('allocator', 0x47EC6A, 0x47ECAE),
    ('letter-pair helper and NULL-safe decoder', 0x493FC0, 0x494214),
    ('XIP acquire and release guards', 0x4763B6, 0x4763E2),
    ('bitmap dispatch', 0x4EB33E, 0x4EB390),
    ('glyph release', 0x4EB390, 0x4EB3EC),
    ('glyph descriptor fallback dispatch', 0x4EB3EC, 0x4EB520),
    ('OTA flag read', 0x44A8D6, 0x44A8E6),
    ('MRAM settings write', 0x481A88, 0x481AB0),
    ('OTA flag write', 0x481B40, 0x481C46),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', type=Path, default=Path('.cache/g2_2.3.2.14.bin'))
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
