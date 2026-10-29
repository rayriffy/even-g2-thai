---
read_when:
  - Changing the Thai font, bitmap storage or mark attachments
  - Reviewing Thai legibility or สระลอย on firmware 2.4.0.24
---

# Maitree ExtraLight for G2

The current candidate uses the actual Maitree ExtraLight outlines. It replaces
the half-resolution A2 font and the rejected hand-drawn/Sarabun experiments.
Visual recognition is assessed against the published face, rather than inferred
from distinct bitmap hashes. Real-glass contrast and optical blur still need a
physical check; the submitted through-lens photograph cannot measure pixel widths.

## Source and weight

[Google Fonts metadata](https://github.com/google/fonts/blob/bd8f81ddb5c74d5c8897b36ad88b440266245103/ofl/maitree/METADATA.pb)
lists ExtraLight as CSS weight 200, the lightest of six weights. The pinned
file is `fonts/maitree/Maitree-ExtraLight.ttf`, version 1.003, SHA-256
`aaa310f9bc913882863b1d39bd70978b7d068ac831ef3789bd921f781392343d`.
The original OS/2 weight class is 275; it is preserved, rather than changed to
match the CSS label. Cadson Demak's copyright and OFL-1.1 license accompany the
font. The [designer's documentation](https://github.com/cadsondemak/maitree)
describes the looped Thai forms and warns about similar consonants and mark placement.

Production renders each outline directly at 16, 20, 24, 28, 32, 36, 40 and 48
pixels with monochrome FreeType. There is no geometric erosion, skeletonization,
half-size raster or enlarged source bitmap. Body shapes and baseline positions
match a direct render of the unmodified source TTF. Natural ascenders,
descenders and curved overshoots remain part of Maitree's design.

Pillow 11.3.0, FreeType 2.13.3 and fontTools 4.66.1 are checked before
regeneration. fontTools exposes the font's existing alternate glyphs through a
memory-only cmap; it changes no outlines, metrics, hinting or vendored file.

## สระลอย and contextual attachment

A lighter face alone cannot repair detached vowels. A mark needs both the
appropriate glyph and an anchor relative to its consonant or previous mark.
[Microsoft's Thai model](https://learn.microsoft.com/en-us/typography/script-development/thai)
describes `ccmp`, `mark` and `mkmk`; the
[Unicode Thai rules](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-16/)
explain outward stacking and SARA AM's ordering exception.

The firmware implements the following finite Maitree rules:

| Context | Font-specific behavior | Review examples |
| --- | --- | --- |
| Ordinary upper/lower marks | Zero advance, attached near the previous right stem | กิ กี กึ กื กุ กู |
| ป/ฝ/ฟ with upper marks | Narrow variants and left attachments clear the tall stem | ปี ปี่ ปี้ ฝิ่น ฟื้น |
| Stacked tones | Smaller high tone forms, mark-to-mark offsets; distinct attachment over ั | นี้ กั่ กิ่ ปั๊ |
| Tone before SARA AM | Separate nikhahit beneath the raised tone; SARA AA keeps its advance | น้ำ ป้ำ |
| ญ/ฐ with lower vowels | Tail-free base forms | ญุ ญู ฐุ ฐู |
| ฎ/ฏ with lower vowels | Font's alternate base and lower mark forms | ฎุ ฏู |
| ฬ with upper marks | Short right finial, with the font's tone+nikhahit exception | ฬิ ฬ่ ฬ่ํ |
| Nikhahit ordering | Raised tone after nikhahit; font ligature when nikhahit follows a tone | กํ่ ก่ํ |
| Thanthakhat above a vowel | Font's smaller contextual sign and stack attachment | กิ์ ปิ์ |

Attachment offsets are rounded to the actual pixel grid. A few native mono
rasters collide by one pixel at small sizes. The generator moves the intact
contextual mark by the minimum displacement needed to clear the stem, vowel
or tail. Outward nikhahit+tone forms are moved only enough to fit the fixed
stock ascent. No glyph is clipped or reduced. Upper vowels are not globally
raised to make room for every possible tone; ordinary marks retain their
Maitree positions. This avoids the excessive empty gap that produces สระลอย.

`tools/maitree_shaping.py` and `patches/thai_shaping.h` select the corresponding
glyphs without modifying UTF-8 storage or decoder offsets. `U+F700..U+F732`
contains 51 internal alternates. Supplementary private-use `U+F0000..U+F0FFF`
encodes attachment adjustments, preserving ordinary BMP private-use UI icons.
This is a finite font-specific shaper, not a general runtime OpenType engine.
Invalid/repeated mark sequences and arbitrary combinations outside the tested
rules are not automatically normalized into valid Thai text.

The independent fixture `fonts/maitree/shaping-reference.json` records 1,936
HarfBuzz 14.4.0 clusters: 44 consonants, ordinary marks, five upper-vowel classes
with four tones, SARA AM, nikhahit ordering and thanthakhat. Glyph selections
and rounded attachments are compared on all eight grids. To reproduce it:

```sh
python3 tools/research_maitree.py build/maitree-shaping-reproduced.json
cmp fonts/maitree/shaping-reference.json build/maitree-shaping-reproduced.json
```

HarfBuzz is a research dependency for that command only. The production build
and on-device renderer do not run it. The final artifact's real decoder is
also executed against every reference case under Unicorn, including original
UTF-8 bytes, offsets and raw lookahead values.

## Stock rendering evidence

The historical 2.3.2.14 SHA-pinned [stock listing](rebases/2.3.2.14-native-font.asm) shows
configuration dispatch at `0x004716FE`. Type 0 returns preloaded font objects.
Type 1 passes a name, mode 1, size and style to `0x004C2DA8`. That call layout
matches LVGL 9.3's
[`lv_freetype_font_create`](https://github.com/lvgl/lvgl/blob/v9.3.0/src/libs/freetype/lv_freetype.h),
whose enum defines mode 1 as outline rendering. Firmware strings also identify
FreeType and Ambiq vector-font paths.

The [2.4.0.24 rebase](rebases/2.4.0.24.md) authenticates the current
font-chain and descriptor integration separately. The six-component OTA
does not contain the external font banks. Their exact
Latin/Japanese families, weights and hinting flags cannot be established from
this image. The patch retains their native callbacks. FreeType's
[grid-fitting guidance](https://freetype.org/freetype2/docs/glyphs/glyphs-3.html)
supports preserving stems and counters; this patch does not claim identical
stock rasterization flags.

## Lossless storage and renderer

Format 5 has 138 dense glyph records per size: 87 native characters and 51
contextual forms. Each six-byte record stores a 16-bit bitmap offset and a
32-bit packed metric word: advance/width/height are six bits each, x is signed
six-bit and y is signed seven-bit. Generation rejects overflow. LVGL's IAR
descriptor remains 32 bytes; disk metrics are unpacked into an eight-byte
internal struct before descriptor construction.

A1 pixels choose the smallest lossless representation: raw rows, identical-row
runs, per-glyph row dictionaries, or a shared palette of exact 4×2 pixel chunks
in column order. Palette indices use one/two bytes, and `0xF0..0xFF` repeats
the previous chunk 1..16 times. Edge padding is ignored outside the original
glyph bounds. The reserved size-table word points to the shared palette.
Chunks retain every bit; they do not replicate one sample across a block.

The 27,304-byte font and 6,424-byte code end at `0x007FDE6C`, leaving 404 bytes
below the authenticated `0x007FE000` flag. All five non-main components remain
stock. Exact local Case-USB bundle/main pins match this candidate and the
same-version stock rollback. Custom BLE and Case staging remain blocked.

Decoding writes directly into caller-owned A8 pixels with the original stride.
It allocates no bitmap heap or scratch image. The bounded 8 KB runtime glyph
cache, allocation-failure fallback, ownership and cache flush are preserved.
Shared copy/metric helpers avoid duplicated code to fit the firmware boundary.

## Validation and previews

Tests verify direct source-outline body identity, distinguish similar
consonants including ท/ฑ, exact round-trip pixels for all 1,104 glyph/size
entries, isolated-pixel/odd-edge positive controls, malformed streams and
packed metrics. Pixel collision/line-box checks cover all 44 consonants with
upper vowels, tones, lower vowels and SARA AM. Artifact emulation checks every
native/alternate bitmap, contextual tag metrics, odd strides, unaligned
descriptors, glyph cache behavior, UTF-8 offsets and native-script controls.

Generated previews are offline pixel evidence. `build/maitree-comparison.png`
compares the source font's shaped render with the fallback.
`build/maitree-alphabet.png` shows the full character set; native-size sample
previews cover all eight sizes. Review them on the glasses before accepting
optical legibility or performance. No physical flash, boot or rollback is
part of this font change.
