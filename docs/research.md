# Thai rendering patch research

## Stock boundary

The authenticated G2 2.2.6.10 Apollo image uses LVGL 9.3.0-dev and FreeType
2.9.1. The first-party font manager builds two four-entry fallback chains:
background and foreground. Their external XIP headers live at `0x80100000` and
`0x80700000`; those font payloads are not present in the downloadable Apollo
main image.

The stock chain builder is at `0x0046CAE0`. Font-manager initialization calls
it at:

- `0x0046D470`, stock bytes `ff f7 36 fb`
- `0x0046D4CE`, stock bytes `ff f7 07 fb`

The patch redirects only those two calls to `thai_chain_build`. The wrapper
calls the stock builder, walks the completed `lv_font_t.fallback` chain, and
attaches a read-only Thai fallback to the final font. The `lv_font_t` layout is
the exact 32-bit LVGL 9.3 layout; `fallback` is at offset `0x1C`.

The IAR target uses short enums. Authenticated stock `lv_font_get_glyph_dsc`
at `0x004D56C0` clears exactly `0x20` bytes, writes the one-byte glyph format at
offset `0x0E`, and uses offset `0x0F` for `is_placeholder`. Stock
`lv_font_glyph_release_draw_data` at `0x004D5664` reads the cache-entry pointer
at offset `0x1C`; therefore `gid.index` is at `0x18`. The injected callback
uses those IAR offsets rather than Clang's default enum ABI.

## Why a bitmap fallback

The stock font binaries are in external XIP storage and their identities and
paths cannot be recovered from the OTA alone. Replacing them would require a
separate font-bank update protocol. Appending a fallback to the Apollo main app
is smaller and preserves stock glyph selection.

The fallback stores Noto Sans Thai alpha masks at eight sizes. Its callbacks
return LVGL 9.3 glyph descriptors and expand packed A4 pixels into LVGL's A8
draw buffer. The callback invokes the active draw-buffer handler's cache flush,
matching LVGL's built-in bitmap-font path.

## Thai shaping boundary

LVGL decodes UTF-8 and supports font fallback, but it does not provide general
Thai OpenType shaping. The patch retains zero advances and FreeType bearings for
combining marks, which makes Thai readable, but it does not execute GPOS
mark-to-base/mark-to-mark tables. Device testing must include stacked vowel and
tone-mark sequences, not only consonants.

### SARA AM and tone marks

Unicode requires the nikhahit component of `U+0E33` SARA AM to render below a
preceding `U+0E48..U+0E4B` tone mark. HarfBuzz achieves this by decomposing SARA
AM to nikhahit plus SARA AA and moving the nikhahit backward across above-base
marks. See the [Unicode Thai combining-mark rule](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-16/),
[HarfBuzz Thai preprocessing](https://chromium.googlesource.com/external/github.com/harfbuzz/harfbuzz/+/refs/heads/upstream/next_range2/src/hb-ot-shaper-thai.cc),
and [Microsoft's Thai OpenType model](https://learn.microsoft.com/en-us/typography/script-development/thai).

The stock rendering-only helper `lv_text_encoded_letter_next_2` is at
`0x00489B3C`; its authenticated first four bytes are `2d e9 f0 41`. Its four
callers are label drawing, text width, width-with-flags, and text size. The
patch replaces its entry with a `B.W` to a wrapper that maps a tone mark whose
next character is SARA AM to `U+F700..U+F703`. Text storage and the global UTF-8
decoder remain untouched.

Each PUA record reuses the original tone bitmap and raises only its `ofs_y`.
The generator computes the smallest per-size displacement that makes all A4
pixels at alpha 4 or higher disjoint from the SARA AM bitmap. This removes the
collision without raising ordinary tone marks such as the one in `เก่ง`.

## Firmware integrity

Injected code and font data are appended after the stock main-app payload. The
patcher updates the main-app subheader size, TOC size, low-24-bit preamble
length, preamble zlib CRC-32, and component CRC-32C. It refuses output beyond
the conservative `0x007F0000` MRAM ceiling, below the OTA flag at `0x007FE000`.
