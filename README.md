# g2-thai

`g2-thai` patches the Even Realities G2 2.2.6.10 firmware with a Thai bitmap
fallback font. It keeps the stock LVGL/FreeType font chains for every existing
glyph and adds Thai only when the stock fonts report a miss.

The project does not redistribute Even's firmware. The build downloads the
vendor image from Even's CDN, verifies its SHA-256, applies a committed binary
patch, verifies every EVENOTA checksum, and writes:

```text
build/g2_2.2.6.10_thai.bin
```

## Build

Clone `g2flash` beside this repository, then run:

```sh
make build
```

`g2flash` supplies the reviewed Thumb-2 compiler helper and the BLE flashing
tool. Set `G2FLASH_ROOT=/path/to/g2flash` if it is elsewhere.

To regenerate the font payload and committed patch after source changes:

```sh
python3 -m pip install -r requirements-dev.txt
make patch
make check
```

Patch regeneration also writes `build/thai-preview.png`, rendered from the
same packed glyph payload and positioning logic used by the firmware callback.

Noto Sans Thai is fetched from a pinned Google Fonts commit and verified before
use. Its generated bitmap data remains covered by the SIL Open Font License in
[`third_party/NotoSansThai-OFL.txt`](third-party/NotoSansThai-OFL.txt).

## Scope and current boundary

- Thai code points `U+0E01..U+0E3A`, `U+0E3F`, and `U+0E40..U+0E5B`.
- Eight raster sizes selected at runtime from the active stock font's line
  height.
- Contextual raised tone-mark alternates for `U+0E48..U+0E4B` immediately
  before `U+0E33` SARA AM, preventing the `น้ำ` nikhahit/tone collision.
- Zero-advance combining marks and Noto's unshaped glyph bearings are retained.
- No HarfBuzz/GPOS engine is added. Thai glyphs render, but complex mark
  positioning outside the implemented SARA AM rule can differ from phone
  typography.
- Offline firmware construction and checksum verification are automated.
  Real-glass rendering and recovery remain hardware validation gates.

Read [`docs/research.md`](docs/research.md) for the hook evidence and
[`docs/flashing.md`](docs/flashing.md) before writing either lens.

## Safety

Custom firmware voids the warranty and can brick a lens. Building never
connects to the glasses. Flashing is a separate, explicit command and should be
preceded by the dry-run and rollback preparation in the flashing guide.

Code is MIT licensed. Generated Noto Sans Thai bitmap data is OFL-1.1.
