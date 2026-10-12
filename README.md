# g2-thai

`g2-thai` patches the Even Realities G2 2.3.2.14 firmware with a Thai bitmap
fallback font. It uses Maitree ExtraLight at native pixel resolution and preserves the stock
LVGL/FreeType paths for Latin, Japanese, and other unrelated glyphs.

The project does not redistribute Even's firmware. The build downloads the
vendor image from Even's CDN, verifies its SHA-256, applies a committed binary
patch, verifies every EVENOTA checksum, and writes:

```text
build/g2_2.3.2.14_thai.bin
```

## Build

Clone `g2flash` beside this repository, then run:

```sh
set -euo pipefail
g2flash_dirty="$(git -C ../g2flash status --porcelain --untracked-files=all | sed '/^?? \.DS_Store$/d')"
test -z "$g2flash_dirty"
git -C ../g2flash checkout --detach 877c8d9490db0d3717ca012dd0f54556af3701bd
test "$(git -C ../g2flash rev-parse HEAD)" = 877c8d9490db0d3717ca012dd0f54556af3701bd
g2flash_dirty="$(git -C ../g2flash status --porcelain --untracked-files=all | sed '/^?? \.DS_Store$/d')"
test -z "$g2flash_dirty"
make build
```

`g2flash` supplies the reviewed Thumb-2 compiler helper. Set
`G2FLASH_ROOT=/path/to/g2flash` if it is elsewhere. Firmware writes use the
vendored WebFlasher Case-USB route documented in [`docs/flashing.md`](docs/flashing.md).

To regenerate the font payload and committed patch after source changes:

```sh
python3 -m pip install -r requirements-dev.txt
make patch
make check
```

Patch regeneration also writes `build/thai-preview.png`, rendered from the
same packed glyph payload and positioning logic used by the firmware callback.

The production font is [Maitree ExtraLight](fonts/maitree/Maitree-ExtraLight.ttf),
the lightest published Google Fonts weight (CSS 200), pinned by SHA-256 and
Google Fonts commit. Its original outlines, advances and hinting remain intact.
The [OFL license](fonts/maitree/OFL.txt) and [source provenance](fonts/maitree/source.json)
are vendored with it. Regeneration uses Pillow 11.3.0, FreeType 2.13.3 and
fontTools 4.66.1. It uses native monochrome rasterization without erosion,
skeletonization or bitmap enlargement.

[Thai font research](docs/thai-pixel-font.md) documents the stock renderer,
Maitree's contextual vowel/tone forms, สระลอย checks, and the lossless storage.
The earlier user-supplied AMD font remains only for historical comparison tests.
Its embedded copyright is "All rights reserved" with no license field; the
existing permission covers this project's reproduction, not reuse elsewhere.

## Firmware updates and rebasing

When the installed glasses version changes, follow the complete
[`docs/firmware-rebase.md`](docs/firmware-rebase.md) playbook before rebuilding
or flashing. It covers official OTA discovery, APK/API analysis, address
relocation, checksum and MRAM gates, rollback evidence, and worked versioned
rebase records.

## Flashing companion (vendored WebFlasher)

Hardware flashes use the charging-case USB writer from AM-Guru's
`evenRealities-webflasher`, vendored as a submodule at
`third_party/evenRealities-webflasher` and carried as
[`patches/webflasher_case_usb_thai.patch`](patches/webflasher_case_usb_thai.patch)
on top of pinned upstream commit `c437fdf`. The patch adds an exact-hash
Case-USB pins for this artifact and its matching stock rollback image
(`localTempleFlashTargets.js`); direct Bluetooth flashing stays rejected.

The companion remains pinned to the reviewed revision with our local-file
support. SybilSight's later removal of custom firmware support is not imported.
The upstream WebFlasher catalog commit `2fcdb888` (October 10, 2026) supplied
the 2.3.2.14 stock provenance, independently verified against Even's CDN; see
[`2.3.2.14 rebase evidence`](docs/rebases/2.3.2.14.md). Load either 2.3.2.14
image from disk; the vendored companion's catalog is older.

```sh
make webflasher
make webflasher-serve
```

The target initializes the submodule, applies the patch idempotently, and
verifies that the writer pin matches the built artifact's bundle and main
payload hashes. `make webflasher-serve` installs the committed WebFlasher
dependencies with `npm ci` before starting Vite, so a fresh checkout does not
fail with `vite: command not found`. Run the vendored project's own tests and
production build inside the submodule before touching hardware.

After a future patch change, run `make patch`, update the local bundle/main
pins, regenerate `patches/webflasher_case_usb_thai.patch` including its new-file
diff, then run `make webflasher` and `node tools/check_webflasher_artifacts.mjs`.
Unknown custom files still fail closed; each build needs its own exact pins.

## Scope and current boundary

- Thai code points `U+0E01..U+0E3A`, `U+0E3F`, and `U+0E40..U+0E5B`.
- Eight native sizes: 16, 20, 24, 28, 32, 36, 40 and 48. Binary A1 pixels
  use lossless row/tile storage; every stored pixel decodes exactly. The fixed
  stock integration line heights and baselines remain unchanged.
- Zero-advance vowels and tones use Maitree's mark attachments, including
  narrower forms on ป/ฝ/ฟ, tail variants for ญ/ฐ/ฎ/ฏ, and the shorter ฬ finial
  under upper marks. SARA AM preserves its nikhahit below the preceding tone.
- The patch implements a finite set of font-specific GSUB/GPOS rules with
  51 contextual glyphs. HarfBuzz is used only as an independent build-time
  research oracle; no general shaping engine runs on the glasses. Tests
  compare 1,936 reference clusters on all eight grids and execute the final
  decoder and bitmap callbacks under emulation.
- Advances follow Maitree instead of the earlier font; Thai text wrapping can change.
- Offline firmware construction and checksum verification are automated.
  Real-glass rendering and recovery remain hardware validation gates.

Read [`docs/research.md`](docs/research.md) for the hook evidence and
[`docs/flashing.md`](docs/flashing.md) before writing either lens.

## Safety

Custom firmware voids the warranty and can brick a lens. Building never
connects to the glasses. Flashing is a separate, explicit command and should be
preceded by the dry-run and rollback preparation in the flashing guide.

Code is MIT licensed. Maitree and its generated bitmap data are OFL-1.1.
