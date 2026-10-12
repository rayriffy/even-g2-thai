# Gates: Maitree ExtraLight Thai font for G2 2.3.2.14

OWNS: fonts/**, build_thai.sh, patches/thai*, tools/*, tests/*, docs/*, README.md, GATES.md, patches/webflasher_case_usb_thai.patch, third_party/evenRealities-webflasher/src/lib/localTempleFlashTargets.js, third_party/evenRealities-webflasher/tests/firmware.test.mjs, third_party/evenRealities-webflasher/README.md

Scope: research stock text rendering, replace the rejected redraw with native-resolution Maitree ExtraLight rasters and contextual Thai shaping, retain all characters/eight sizes and Thai mark shaping, fit the authenticated firmware boundary, and produce a locally verified Case-USB candidate.

- [x] G1: Stock font research and photo/code diagnosis distinguish confirmed facts from unavailable native assets
  EVIDENCE: docs/thai-pixel-font.md and authenticated native-font listing establish outline/preloaded paths; missing XIP banks and photo defocus limits explicitly retained.
- [x] G2: Rebuilt firmware passes all regression and emulation checks
  CHECK: rtk proxy env PATH=/Users/rayriffy/Git/g2-thai/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin make check
  EXPECT: /^OK$/m
  EVIDENCE: automatic-evidence=v1; definition-sha256=bc67684ade4284fc7d080008250d765e721b99d555f9275280c36d132193ff87; exit=0; EXPECT=matched; output-sha256=e0ae90380256a25f022f65d763fb13ac31f2da5e3b6039f2040e8265ff4a6817; output-bytes=11368; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G3: Maitree font retains every Thai character/eight sizes, native font forms, shared baseline and attached vowels; tall and descending consonants, stacked tones and SARA AM covered
  EVIDENCE: Direct unmodified Maitree ExtraLight TTF body/baseline identity at eight grids; all87 characters retained; 1936 HarfBuzz selections/rounded attachments match across8 sizes; all44-consonant vowel/tone/line-box checks pass.
- [x] G4: WebFlasher exact pins accept the new candidate and rollback and reject mutations
  CHECK: rtk proxy /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/check_webflasher_artifacts.mjs
  EXPECT: WEBFLASHER_ARTIFACTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=23c940328866e8961b6beb911d5d025f956204c95828660b43dba90ed0a060c3; exit=0; EXPECT=matched; output-sha256=92cf440f4f0a923db1fdc264ae3fe456e3253bfaca614e744db897476de42980; output-bytes=180; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G5: Lossless full-resolution bitmap decoding is proven against known controls and final artifact execution
  EVIDENCE: Exact round trips for1104 native/contextual glyph-size entries and isolated-pixel/odd-edge controls; final Thumb bitmap callbacks, tags, alignment, stride and cache paths pass emulation.
- [x] G6: Source reproduction, container preservation, size limit, companion tests/build and portable patch pass
  EVIDENCE: Pinned font source and HarfBuzz fixture reproduce; all5 non-main components unchanged, stock+candidate pass independent G2Flash validation, end7FDE6C below7FE000 by404 bytes;345 JS+25 Python tests and Vite build pass; portable patch applies across12 files with byte-identical output.
- [x] G7: Typeface previews, documentation and independent change review pass
  EVIDENCE: Source-vs-firmware comparison and full alphabet inspected; eight native-size previews generated; docs/OFL/source provenance current; autoreview --mode local --model codex=gpt-5.5 completed clean with zero findings (build/maitree-autoreview.json).

Hardware boundary: no flashing requested. Actual frame rate, GPU timing, boot and rollback require physical validation; offline instruction counts do not establish FPS parity.
Discovery: indexed `Maitree` search was empty; indexed decoder search located patches/thai_font.c. Native source and font inspection used for the new input. The existing A2 codec downsamples then replicates samples 2x2; the redesign must remove that loss. No device writes are part of this request. The user approved the Maitree candidate and authorized commit/push on 2026-10-12.
