#!/usr/bin/env python3
"""Compare real Thumb instructions in two firmware artifacts; never estimate FPS."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from font_perf_fixture import FontFixture

SAMPLES = {
    'repeat': 'ก' * 32,
    'sentence': 'สวัสดีครับวันนี้อากาศดีน้ำเก่งนี้ทดสอบภาษาไทยกรุงเทพมหานคร',
    'thrash': 'กขคงจฉชซญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ',
}


def measure(artifact, spec, size, text):
    f = FontFixture(artifact, spec)
    vm = f.vm
    root, native = f.chain(size=size)
    runtime = vm.read_word(native[-1] + 28)
    text_ptr = vm.utf8(text)
    codepoints, offset = [], 0
    # Use the actual contextual text hook, including its raised-tone variants.
    while True:
        cp, next_cp, offset = vm.decode_step(text_ptr, offset)
        if not cp:
            break
        codepoints.append((cp, next_cp))
    dsc, pixels, draw, handlers = (vm.alloc(n) for n in (32, 2048, 32, 32))
    vm.write_words(handlers, [0, 0, 0, 0, vm.flush_stub | 1, 0, 0, 0])
    vm.write_words(draw + 16, [pixels, 0, handlers])
    scratch = vm.ram_next
    frames = []
    digest = hashlib.sha256()
    for frame in range(3):
        lookup_instructions = bitmap_instructions = hits = 0
        before_callbacks, before_guards = len(f.callbacks), len(f.guards)
        before_flushes = f.flushes
        for cp, next_cp in codepoints:
            before = f.instructions
            result, raw = f.lookup(root, cp, next_cp)
            lookup_instructions += f.instructions - before
            assert result == 1
            vm.ram_next = scratch
            vm.uc.mem_write(dsc, raw)
            width, height = struct.unpack_from('<HH', raw, 6)
            stride = (width + 3) & ~3
            vm.uc.mem_write(draw + 8, struct.pack('<H', stride))
            vm.uc.mem_write(pixels, b'\0' * (stride * height))
            cached = [vm.read_word(runtime + 48 + slot * 8) for slot in range(4)]
            hits += cp in cached
            before = f.instructions
            assert vm.call(f.fonts[size]['bitmap'], [dsc, draw]) == draw
            bitmap_instructions += f.instructions - before
            digest.update(bytes(vm.uc.mem_read(pixels, stride * height)))
            digest.update(raw[4:])  # exclude relocated resolved-font address
        assert f.flushes - before_flushes == len(codepoints)
        frames.append(dict(frame=frame, glyphs=len(codepoints), cache_hits=hits,
                           lookup=lookup_instructions, bitmap=bitmap_instructions,
                           native_callbacks=len(f.callbacks) - before_callbacks,
                           xip_guards=len(f.guards) - before_guards))
    return dict(sha256=f.sha256, pixels_and_metrics_sha256=digest.hexdigest(), frames=frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    baseline = args.baseline
    rows = []
    for size in (16, 20, 24, 28, 32, 36, 40, 48):
        for name, text in SAMPLES.items():
            before = measure(baseline / 'g2_2.2.10.10_thai.bin',
                             baseline / 'thai_patches.json', size, text)
            after = measure(ROOT / 'build/g2_2.3.0.24_thai.bin',
                            ROOT / 'patches/thai_patches.json', size, text)
            assert before['pixels_and_metrics_sha256'] == after['pixels_and_metrics_sha256']
            for old, new in zip(before['frames'], after['frames']):
                assert old['cache_hits'] == new['cache_hits']
                assert new['native_callbacks'] == new['xip_guards'] == 0
                assert new['lookup'] < old['lookup']
                assert new['lookup'] + new['bitmap'] < old['lookup'] + old['bitmap']
            rows.append(dict(size=size, sample=name, before=before, after=after))
    totals = {version: {phase: sum(frame[phase] for row in rows
                                  for frame in row[version]['frames'])
                        for phase in ('lookup', 'bitmap')}
              for version in ('before', 'after')}
    assert totals['after']['bitmap'] < totals['before']['bitmap']
    native_controls = []
    for cp in (ord('A'), 0x4E2D, 0xAC00):
        controls = []
        for artifact, spec in (
            (baseline / 'g2_2.2.10.10_thai.bin', baseline / 'thai_patches.json'),
            (ROOT / 'build/g2_2.3.0.24_thai.bin', ROOT / 'patches/thai_patches.json')):
            f = FontFixture(artifact, spec)
            root, _ = f.chain()
            f.native_result = True
            before_count = f.instructions
            result, raw = f.lookup(root, cp)
            controls.append(dict(instructions=f.instructions - before_count,
                                 result=result, descriptor=raw[4:].hex()))
        assert controls[0]['descriptor'] == controls[1]['descriptor']
        assert controls[0]['result'] == controls[1]['result'] == 1
        overhead = controls[1]['instructions'] - controls[0]['instructions']
        assert overhead <= (7 if cp < 128 else 16), overhead
        native_controls.append(dict(codepoint=hex(cp), controls=controls,
                                    overhead_instructions=overhead))
    report = dict(method='Unicorn ARM Thumb instruction counts; native font callbacks, '
                         'XIP guards and flush stubbed; no GPU or wall-time/FPS claim',
                  samples=SAMPLES, totals=totals, results=rows, native_controls=native_controls)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(totals))
    print('PERFORMANCE_OK: identical pixels/metrics across 8 sizes and 3 workloads')


if __name__ == '__main__':
    main()
