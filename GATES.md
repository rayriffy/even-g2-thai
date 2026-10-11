# Gates: G2 Thai 2.3.2.14 rebase

OWNS: build_thai.sh, patches/thai*, tools/*, tests/*, docs/*, README.md, GATES.md, patches/webflasher_case_usb_thai.patch, third_party/evenRealities-webflasher/src/lib/localTempleFlashTargets.js, third_party/evenRealities-webflasher/tests/firmware.test.mjs, third_party/evenRealities-webflasher/README.md

Scope: authenticate stock 2.3.2.14, relocate the Thai patch, fit its install window using user-approved smaller bitmaps while retaining all Thai characters and eight sizes, and preserve Case-USB acceptance with same-version rollback.

- [x] G1: Stock provenance, exact hooks, decoder dispatch and install boundary have binary evidence
  EVIDENCE: Independently authenticated official OTA and all six components; unique version-specific anchors, decoded final branches, exactly two builder callers, double-indirect decoder verified. SHA-pinned disassembly authenticates OTA 0x7FE000 and settings 0x7FF000. Pinned G2Flash validates both images with the scoped authenticated ceiling override; source repository unchanged.
- [x] G2: Rebuilt firmware passes all regression and emulation checks
  CHECK: rtk proxy env PATH=/Users/rayriffy/Git/g2-thai/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin make check
  EXPECT: OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=4af54b6b8371bfcd8db0b2e6e4c6e4449585f7ba221e5807d3354c97926bab20; exit=0; EXPECT=matched; output-sha256=271ebb8967f30e2cec52f3e32b27f019be0312a1eff928448ebcb37b53084d49; output-bytes=9443; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G3: Compact storage retains every Thai character and eight metric sets, with visible marks and bounded expansion
  EVIDENCE: 64 firmware tests pass, including compact reproduction and every significant source stroke, all eight coverage/metric sets, SARA AM dot and contextual-mark separation, native fallback/register controls, all-glyph bitmap expansion with odd/unaligned strides, and cache ownership. Preview visually checked; 24,147-byte A2 font and 4,680-byte code end at 0x7FCB47, leaving 5,305 bytes before the flag. No extra bitmap allocation.
- [x] G4: WebFlasher exact pins accept the candidate and rollback and reject mutations
  CHECK: rtk proxy /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/check_webflasher_artifacts.mjs
  EXPECT: WEBFLASHER_ARTIFACTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=23c940328866e8961b6beb911d5d025f956204c95828660b43dba90ed0a060c3; exit=0; EXPECT=matched; output-sha256=92cf440f4f0a923db1fdc264ae3fe456e3253bfaca614e744db897476de42980; output-bytes=180; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G5: Companion tests/build, reproducibility, portable patch and review pass
  EVIDENCE: 345 WebFlasher tests, 25 companion Python tests and production build pass. Fresh pinned-baseline patch application reproduces all 12 files and updated 2.3.2.14 README instructions. Source regeneration byte-matches thai_patches.json; final artifact SHA-256 e6e1f569d1f50e64690cd546fbba400eed6067e0dc674d5fd3c00a1dabe5f609 agrees with record and writer pins. Final Codex/gpt-5.5 autoreview exited 0 with no actionable findings; result saved in build/g2-2.3.2.14-review-final.json. git diff --check clean.

Hardware boundary: no flashing requested. Actual frame rate, GPU timing, boot and rollback require physical validation; offline instruction counts do not establish FPS parity.
Discovery: indexed symbol query `generate_patch` found tools/generate_patch.py. Exact current reads established the 2.3.0.24 baseline. Upstream metadata staged in /tmp, pinned to 2fcdb888facfe9c56672cbe2a3da741b44033c44. Binary-dispatched emulation coverage is checked explicitly too.
