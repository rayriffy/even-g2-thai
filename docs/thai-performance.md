# Thai rendering performance, 2.2.10.10

Read when investigating dropped frames, changing glyph callbacks, rebuilding
the performance candidate, or comparing it on hardware.

The September 15 candidate removes native-font misses ahead of the injected
Thai font and reduces descriptor/cache-copy work. The emulator measures **63.0%
fewer lookup instructions, 5.8% fewer bitmap instructions, and 12.8% fewer
combined instructions** than the September 10 rebase. These are CPU instruction
counts, not frame rates. Actual near-native performance remains unverified.

## Stock decompilation

The exact stock OTA SHA-256 is
`927879057685a4147c6ba1fe33e5f3740d3cc48f87141a9039204d94516e65b8`.
[The bounded Thumb listing](rebases/2.2.10.10-font-path.asm) is generated from
that file by `tools/disassemble_font_path.py`. Below is manually reconstructed
C-like control flow from those instructions, not recovered vendor source.
The external font banks at `0x80100000` / `0x80700000` are absent from the OTA;
their glyph callbacks cannot be fully executed or decompiled from this bundle.

```c
// 0x004E8D90: lv_font_get_glyph_dsc; assertion/logging blocks abbreviated
assert(font && out);
memset(out, 0, 32);                         // 0x004E8DEC
first_placeholder = NULL;
XIP_BASE = 0x80000001;                      // literal at 0x004E8F3C
for (candidate = font; candidate; candidate = candidate->fallback) {
    assert(candidate->get_glyph_dsc >= 0x101);
    if (candidate->dsc >= XIP_BASE) xip_enter(); // 0x004E8DFA..0x004E8E00
    next = candidate->kern_disabled ? 0 : letter_next;
    found = candidate->get_glyph_dsc(candidate, out, letter, next);
    if (candidate->dsc >= XIP_BASE) xip_exit();
    if (found && !out->is_placeholder) {
        out->resolved_font = candidate;     // 0x004E8E56
        return true;
    }
    if (found && !first_placeholder) first_placeholder = candidate;
}
if (first_placeholder) {
    // Retry its callback with the same XIP guards and kerning policy.
    get_placeholder_again(first_placeholder, out, letter, letter_next);
    out->resolved_font = first_placeholder;
    return true;
}
// No font: adv=4, width=2, height=font->line_height, format=1, placeholder=1.
fill_missing_glyph(out, font);
return false;

// 0x004E8CE2: bitmap dispatch
font = out->resolved_font;
assert(font);
if (font->dsc >= XIP_BASE) xip_enter();
result = font->get_glyph_bitmap(out, caller_draw_buffer);
if (font->dsc >= XIP_BASE) xip_exit();
return result;

// 0x004E8D34: glyph release
if (out->entry && out->resolved_font && out->resolved_font->release_glyph) {
    // Same XIP guards surround the release callback.
    out->resolved_font->release_glyph(out->resolved_font, out);
}
```

`xip_enter` at `0x004760EA` calls `0x00476030`, examines a runtime state byte,
and conditionally calls `0x00475FB6`. `xip_exit` at `0x00476100` conditionally
calls `0x00475F96`, then `0x0047608E`. They are real function calls beyond the
descriptor loop; their runtime latency is not included in the benchmark.

The previous patch appended Thai after four native fonts. For covered Thai,
every descriptor lookup therefore attempted those four fonts first. This cost
occurs during measurement as well as drawing. A bitmap-cache hit does not avoid
it. A second observed limit is the four-slot cache: the 58-glyph sentence below
has only five hits per frame. The optimization does not claim to eliminate that
cache thrashing or establish which cost dominates real dropped frames.

## Retained changes

- A four-byte branch at `0x004E8D90` selects our covered Thai/PUA glyphs directly
  when the requested chain contains the exact injected descriptor callback.
  It walks at most 12 pointers without calling earlier font callbacks. A
  present glyph gets the same resolved Thai font, metrics, flags and empty
  release entry as the original dispatcher. Absent glyphs and chains without
  our callback resume stock lookup. In patched chains, our covered Thai glyphs
  intentionally take precedence over any earlier font's Thai glyphs; adding a
  future Thai-capable native font bank requires revisiting this policy.
- The original `push.w {r1-r11,lr}` is replayed by a trampoline, which resumes
  stock at `0x004E8D94`. ASCII takes a short assembly guard without another C
  stack frame. Native-success controls add seven instructions for ASCII and
  fourteen for CJK/Hangul; native selection, kerning and placeholders match.
- Aligned 32-byte glyph descriptors use eight word stores. Unaligned callers
  retain byte stores; all four alignments match for every supported glyph.
- Cache transfers with no row padding use a single contiguous copy. Padded or
  unusual strides keep the previous row copies. SRAM allocation, four slots,
  8 KiB budget, reentrancy fallback and flush behavior are unchanged.

The A4 blob remains byte-identical:
`0214e9c861d8643bd09126cfba1634370ff43ab241c95cb6c722999a77a7e6ba`.
No glyph pointers are lent to the GPU, no caller-owned buffer is replaced,
and no new heap allocation or cache lifetime rule is introduced.

## Reproducible measurement

`tools/benchmark_thai.py` executes actual baseline/candidate Thumb code under
Unicorn. Native font callbacks, XIP guards and cache flush are explicit stubs
because the external font banks and hardware are unavailable. It measures
lookup plus bitmap callbacks, excluding layout, display transfer and GPU time.
There are eight sizes, three workloads, three frames per workload: 72 measured
frames. Every pixel and descriptor field except relocated font pointers matches.

| Work | Previous instructions | Candidate instructions | Reduction |
| --- | ---: | ---: | ---: |
| Glyph lookup | 1,020,384 | 377,952 | 63.0% |
| Bitmap callback | 7,304,636 | 6,884,358 | 5.8% |
| Combined | 8,325,020 | 7,262,310 | 12.8% |
| Repeated glyph workload, combined | 1,171,966 | 895,559 | 23.6% |
| Thai sentence workload, combined | 3,851,109 | 3,387,852 | 12.0% |
| Cache-thrashing workload, combined | 3,301,945 | 2,978,899 | 9.8% |

Samples are `ก` repeated, a Thai sentence containing `น้ำ`, `เก่ง`, `นี้`, and
40 distinct consonants. The real contextual decoder selects raised tone glyphs.
The benchmark asserts improvement for every size/workload/frame combination,
pixel/metric equality, and native-control overhead bounds.

Run with the repo's declared Python dependencies. To recreate the baseline
without switching branches:

```sh
mkdir -p build/perf-baseline
git show dbd98339046bfc62a6b6969c5432909f584c72c6:patches/thai_patches.json > build/perf-baseline/thai_patches.json
python3 tools/apply_patches.py .cache/g2_2.2.10.10.bin build/perf-baseline/thai_patches.json build/perf-baseline/g2_2.2.10.10_thai.bin
python3 tools/benchmark_thai.py --baseline build/perf-baseline --output build/thai-performance.json
python3 tools/disassemble_font_path.py --output build/stock-font-path.asm
make check
```

Baseline SHA-256:
`cad29efb784121ece18207989bb7f9d57e2ba4a1349883dd3689f89de5654308`.
Candidate SHA-256:
`92ba54d4203e97e426425385eec98af8aeb801d0faacb95c2e54ab9b3308452f`.
Candidate size: 4,631,387 bytes; main payload: 3,852,206 bytes. Injected code:
5,304 bytes, 840 more than baseline. Programmed end: `0x007E478E`, leaving
47,218 bytes under `0x007F0000`. The five non-main components are unchanged.

## Verification

- `make check`: 56 tests passed, including generated-artifact emulation, all
  descriptor alignments, native kerning/placeholders/register preservation,
  shaping, buffer bounds and unchanged stock regions.
- Benchmark: all 72 cases passed with pixel/metric equality and one flush per glyph.
- Fresh compilation reproduced `patches/thai_patches.json` byte-for-byte.
- Independent pinned G2Flash validated six components in stock and candidate.
- WebFlasher parser/writer accepted exact candidate and rollback; payload
  mutations and unknown hashes were rejected. Its 158 relevant tests and
  production build passed. The portable patch reproduced all 12 files in a
  fresh extraction of the pinned companion.

## Hardware handoff

The local Case-USB allowlist pins this candidate and the same-version official
rollback. Nothing was flashed. Compare the same dashboard, Thai scrolling text,
notification and mixed Latin/Thai/CJK content against the baseline on one temple.
Use fixed brightness/content and repeat each scene; inspect smoothness, missed
frames, tone placement, navigation and repeated dashboard creation. Offline
proof covers branch/ABI behavior, bounds, pixels and container integrity; it
does not cover boot, GPU coherency, physical rollback or near-native FPS.
