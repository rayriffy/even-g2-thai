# g2-thai

`g2-thai` patches the Even Realities G2 2.4.0.24 firmware with a Thai bitmap
fallback font. It uses Maitree ExtraLight at native pixel resolution and preserves the stock
LVGL/FreeType paths for Latin, Japanese, and other unrelated glyphs.

The project does not redistribute Even's firmware. The build downloads the
vendor image from Even's CDN, verifies its SHA-256, applies a committed binary
patch, verifies every EVENOTA checksum, and writes:

```text
build/g2_2.4.0.24_thai.bin
```

## Build

From a plain clone, run:

```sh
make build
```

The build initializes [`third_party/g2flash`](https://github.com/jimrandomh/g2flash)
automatically at reviewed commit `877c8d9490db0d3717ca012dd0f54556af3701bd`.
It supplies the Thumb-2 compiler helper; no sibling checkout is needed.
Existing helper checkouts must match that revision and have no source changes.
Set `G2FLASH_ROOT=/path/to/g2flash` to use a separately managed checkout with
the same checks. Firmware writes use the
vendored WebFlasher Case-USB route documented in [`docs/flashing.md`](docs/flashing.md).

To regenerate the font payload and committed patch after source changes:

```sh
python3 -m pip install -r requirements-dev.txt
make patch
make check
```

Patch regeneration also writes `build/thai-preview.png`, rendered from the
same packed glyph payload and positioning logic used by the firmware callback.

GitHub Actions derives archive paths and the artifact name from the committed
patch's firmware version. `python3 tools/prepare_ci_artifact.py` verifies the
built image against its patch/rebase digests and renders the preview from the
embedded font before packaging the firmware, checksum manifest, current rebase
evidence and font license. This keeps archive inputs aligned after a rebase.

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

Configure the extracted app constants locally as described in the
[firmware URL guide](docs/firmware-download.md), then resolve a public G2 or R1 URL:

```sh
python3 even_firmware.py --save-login --email you@example.com --serial YOUR_G2_SERIAL
python3 even_firmware.py --firmware-version 2.4.0.24 --json
python3 even_firmware.py --r1 --serial YOUR_R1_SERIAL --json
```

The first command saves the login in macOS Keychain; later G2 and R1 requests
reuse it. The client prints metadata and URLs without downloading or flashing.
See the [firmware URL guide](docs/firmware-download.md) for version overrides,
login removal, environment variables and tests, and the
[Android 2.4.0 protocol evidence](docs/protocol.md) for the recovered request contract.

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
The 2.4.0.24 stock provenance comes from the supplied Even update metadata;
two Even CDN downloads matched byte-for-byte, including the published MD5 and
size. See [`2.4.0.24 rebase evidence`](docs/rebases/2.4.0.24.md).
Load either 2.4.0.24 image from disk; the vendored companion's catalog is older.

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
