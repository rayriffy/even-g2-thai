#!/usr/bin/env python3
"""Reproduce the build-independent HarfBuzz Thai shaping reference fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from pixel_font import SOURCE, SOURCE_SHA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Maitree source digest mismatch')
    version = subprocess.check_output(['hb-shape', '--version'], text=True).strip()
    if version != 'hb-shape (HarfBuzz) 14.4.0':
        raise ValueError('reference capture requires hb-shape 14.4.0')
    by_base = {}
    for cp in range(0x0E01, 0x0E2F):
        if cp in (0x0E24, 0x0E26):
            continue  # Vocalic letters are not consonant bases.
        base = chr(cp)
        texts = [base + m for m in 'ัิีึืฺุู็่้๊๋์ํ๎']
        texts += [base + v + t for v in 'ัิีึื' for t in '่้๊๋']
        texts += [base + t + 'ำ' for t in '่้๊๋']
        texts += [base + 'ำ', base + '่ํ', base + 'ํ่', base + 'ิ์']
        output = subprocess.run(['hb-shape', str(SOURCE), '--output-format=json', '--no-glyph-names'],
                                input='\n'.join(texts) + '\n', text=True, capture_output=True, check=True)
        shaped = [json.loads(line) for line in output.stdout.splitlines()]
        if len(shaped) != len(texts):
            raise ValueError('incomplete HarfBuzz output')
        by_base[base] = {text: [{key: glyph[key] for key in ('g', 'dx', 'dy', 'ax')} for glyph in glyphs]
                         for text, glyphs in zip(texts, shaped)}
    text = '{\n  "source_sha256": ' + json.dumps(SOURCE_SHA) + ',\n  "harfbuzz": "14.4.0",\n  "units_per_em": 1000,\n  "cases": {\n'
    text += ',\n'.join('    ' + json.dumps(base, ensure_ascii=False) + ': ' + json.dumps(cases, ensure_ascii=False)
                       for base, cases in by_base.items())
    args.output.write_text(text + '\n  }\n}\n')
    print(f"Captured {sum(len(cases) for cases in by_base.values())} OpenType references")


if __name__ == '__main__':
    main()
