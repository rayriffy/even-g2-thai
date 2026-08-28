# Thai rendering patch research

For the version-independent OTA discovery, app-analysis, binary relocation,
and verification procedure, read the
[firmware discovery and rebase playbook](firmware-rebase.md).

## Stock boundary

The authenticated G2 2.2.9.22 Apollo image uses LVGL 9.3.0-dev and FreeType
2.9.1. The first-party font manager builds two four-entry fallback chains:
background and foreground. Their external XIP headers live at `0x80100000` and
`0x80700000`; those font payloads are not present in the downloadable Apollo
main image.

The rebase uses the vendor bundle with SHA-256
`a03fbea9f68a9de6bc271daabb9f3a41c59053d1086622c76a4e990f829cc561`.
Its main payload begins at OTA offset `0x000BE3E2`, is `0x00386A84` bytes, and
maps through file delta `0x00379BFE`. None of the earlier addresses were
carried forward by assumption: exact binary anchors uniquely relocated every
dependency below, and the decoded Thumb-2 branches at both hook sites still
target the relocated stock chain builder.

The stock chain builder is at `0x00470988`. Font-manager initialization calls
it at:

- `0x00471318`, stock bytes `ff f7 36 fb`
- `0x00471376`, stock bytes `ff f7 07 fb`

The patch redirects only those two calls to `thai_chain_build`. The wrapper
calls the stock builder, walks the completed `lv_font_t.fallback` chain, and
attaches a read-only Thai fallback to the final font. The `lv_font_t` layout is
the exact 32-bit LVGL 9.3 layout; `fallback` is at offset `0x1C`.

The IAR target uses short enums. Authenticated stock `lv_font_get_glyph_dsc`
at `0x004E64FC` clears exactly `0x20` bytes, writes the one-byte glyph format at
offset `0x0E`, and uses offset `0x0F` for `is_placeholder`. Stock
`lv_font_glyph_release_draw_data` at `0x004E64A0` reads the cache-entry pointer
at offset `0x1C`; therefore `gid.index` is at `0x18`. The injected callback
uses those IAR offsets rather than Clang's default enum ABI.

## Why a bitmap fallback

The stock font binaries are in external XIP storage and their identities and
paths cannot be recovered from the OTA alone. Replacing them would require a
separate font-bank update protocol. Appending a fallback to the Apollo main app
is smaller and preserves stock glyph selection.

The fallback stores `2005_iannnnnAMD` alpha masks at eight stock target sizes,
rasterized at 2× source resolution because this font's Thai glyph design is
visually about half the requested pixel size. Host-side Raqm shaping extracts
combining marks without the font's dotted-circle scaffolds and synthesizes
U+0E33 SARA AM from shaped U+0E4D nikhahit plus U+0E32 sara aa. The production
raster is first supersampled from the source outline, then geometrically
eroded and downsampled back to device size. This creates a fractional stroke
contraction instead of dimming the original outline. `--thin 1` removes half a
device pixel from each contour; `--thin 2` removes one, falling back by a
high-resolution pixel only when a tiny mark would disappear. Production stays
at `--thin 1` unless a preview is visually approved. Its callbacks return LVGL
9.3 glyph descriptors and expand packed A4 pixels into LVGL's A8 draw buffer.
The callback invokes the active draw-buffer handler's cache flush, matching
LVGL's built-in bitmap-font path.

## Rendering cost

The firmware converts each embedded glyph from packed A4 to LVGL A8 in the
draw buffer. Aligned rows expand two output pixels per packed byte with a
single 16-bit store from a 256-entry pair lookup; unusual unaligned rows retain
the byte-safe lookup path. Both preserve exact A8 values and the mandatory
cache flush. The only context-sensitive decoder case—tone marks after upper
Thai marks—now identifies the immediately preceding fixed-width Thai UTF-8
sequence directly instead of re-decoding the text prefix.

## Thai shaping boundary

LVGL decodes UTF-8 and supports font fallback, but it does not provide general
Thai OpenType shaping. The build pre-bakes the required mark anchors, SARA AM,
and raised tone variants into bitmap records; firmware does not execute GPOS
mark-to-base/mark-to-mark tables. The decoder classifies preceding upper Thai
marks, so a following tone selects the raised variant for any valid future
cluster such as `นี้`, rather than matching a word list. Device testing must include stacked vowel and
tone-mark sequences, not only consonants.

### SARA AM and tone marks

Unicode requires the nikhahit component of `U+0E33` SARA AM to render below a
preceding `U+0E48..U+0E4B` tone mark. HarfBuzz achieves this by decomposing SARA
AM to nikhahit plus SARA AA and moving the nikhahit backward across above-base
marks. See the [Unicode Thai combining-mark rule](https://www.unicode.org/versions/Unicode17.0.0/core-spec/chapter-16/),
[HarfBuzz Thai preprocessing](https://chromium.googlesource.com/external/github.com/harfbuzz/harfbuzz/+/refs/heads/upstream/next_range2/src/hb-ot-shaper-thai.cc),
and [Microsoft's Thai OpenType model](https://learn.microsoft.com/en-us/typography/script-development/thai).

The stock rendering-only helper `lv_text_encoded_letter_next_2` is at
`0x00491BA4`; its authenticated first four bytes are `2d e9 f0 41`. Five direct
call sites cover label drawing and text measurement paths. The helper obtains
its UTF-8 decoder through the double pointer at `0x00491F14` (slot address,
then function pointer, runtime-initialized by the firmware) and calls the
decoder's lookahead pass with a NULL offset argument; the decoder at
`0x00491CC6` substitutes a stack slot when the offset pointer is NULL. An
earlier wrapper revision called `0x00491E24` directly, misidentified as the
UTF-8 helper; its prologue dereferences the offset pointer unconditionally and
faulted on that NULL lookahead on every multi-character label. The patch
replaces the helper's entry with a `B.W` to a wrapper that resolves the decoder
through `0x00491F14`, maps a tone mark whose next character is SARA AM to
`U+F700..U+F703`, and leaves text storage and the global UTF-8 decoder
untouched.

Each PUA record reuses the original tone bitmap and raises only its `ofs_y`.
The generator computes the smallest per-size displacement that makes all A4
pixels at alpha 4 or higher disjoint from the SARA AM bitmap. This removes the
collision without raising ordinary tone marks such as the one in `เก่ง`.

## Stock font architecture and the CJK pipeline

Binary strings and relocated code in 2.2.9.22 show how stock renders non-Latin
scripts:

- LVGL 9.3 integrates FreeType 2.9.1 (`lv_freetype_font_create`,
  `lv_freetype_set_cbs_outline_font`, `lv_freetype_set_cbs_image_font`) plus an
  Ambiq vector draw layer (`lv_draw_ambiq_vector_font.c`,
  `lv_draw_ambiq_vector_font_ft_cb`).
- The first-party `lvgl_font_manager.c` builds the two fallback chains this
  patch extends ("Font initialization completed - background: %p,
  foreground: %p") from static configs through `font_manager_create_chain`.
- Fonts come in two kinds: runtime-rasterized FreeType vector fonts, and
  precompiled binary fonts loaded from external XIP flash
  (`XIP font load from flash, Name = %s`; utility examples reference
  `s200_font.bin` at `0x80100000`).
- Font banks have their own OTA channel (`eOTATransmitType_FONT`), independent
  of Apollo firmware updates.
- UI language is a settings index (`SVC_KvdbReadLanguage`,
  `set_general_configure_language`).
- There is no HarfBuzz and no shaping engine anywhere in the image. Chinese
  needs none (per-character han), Korean renders from precomposed hangul
  syllables, so the FreeType path suffices. No Thai strings or Thai font exist
  in stock; Thai is not an officially supported device language.

The Thai fallback therefore reuses stock's integration surface while differing
in glyph source: it appends a standard callback-based `lv_font_t` to the same
manager-built chains (identical interface to FreeType's callback fonts), but
serves precomputed A4-packed Noto Sans Thai bitmaps embedded in the Apollo
append instead of rasterizing a TTF from the un-reversed font-bank protocol.
That keeps the patch inside one OTA, heap-free, and deterministic, at the cost
of fixed sizes (8) and coverage (132 codepoints) versus arbitrary vector
rendering.

## Firmware integrity

Injected code and font data are appended after the stock main-app payload. The
patcher updates the main-app subheader size, TOC size, low-24-bit preamble
length, preamble zlib CRC-32, and component CRC-32C. It refuses output beyond
the conservative `0x007F0000` MRAM ceiling, below the OTA flag at `0x007FE000`.
