# Gates: G2 firmware 2.2.10.10 rebase

Scope: authenticate firmware 2.2.10.10, relocate every Thai patch dependency, rebuild the OTA, and verify its Case-USB writer integration.

Execution note: checks below were run directly and their results recorded here.
The companion's npm uses the installed npm CLI through a temporary launcher
with the bundled Node runtime; no project dependency versions were changed.

- [x] G0: this ledger states executable outcomes that can fail
  CHECK: /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node /Users/rayriffy/.agents/skills/unlazy/scripts/gate-lint.mjs GATES.md
  EXPECT: LINT OK
  EVIDENCE: gate-lint exited 0 with LINT OK; two expected warnings identify the manual review and browser/reproduction gates.

- [x] G1: the rebased firmware builds and all firmware tests pass
  CHECK: rtk proxy env PATH=/Users/rayriffy/Git/g2-thai/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin make check
  EXPECT: Ran 48 tests
  EVIDENCE: /bin/sh; cwd=/Users/rayriffy/Git/g2-thai; exit=0; 48 tests passed, zero skips; built SHA-256 cad29efb784121ece18207989bb7f9d57e2ba4a1349883dd3689f89de5654308.

- [x] G2: the rebuilt OTA has a valid six-component container
  CHECK: PATH="/Users/rayriffy/Git/g2-thai/.venv/bin:$PATH" python3 tools/verify_firmware.py build/g2_2.2.10.10_thai.bin
  EXPECT: verified 6 EVENOTA components
  EVIDENCE: exit=0; project verifier and independent pinned g2flash.validate_firmware both validated stock and patched six-component bundles; all five non-main components preserved.

- [x] G3: WebFlasher accepts exactly the rebased local artifact
  CHECK: PATH="/Users/rayriffy/Git/g2-thai/.venv/bin:$PATH" make webflasher
  EXPECT: webflasher pin matches artifact
  EVIDENCE: exit=0; bundle pin cad29efb784121ece18207989bb7f9d57e2ba4a1349883dd3689f89de5654308; main pin 050863006aef8c0d47a730c51410c192155b39c04bbb106c05d1c7a424e9711b; 3851366 bytes.

- [x] G4: the vendored WebFlasher tests and production build pass
  CHECK: rtk proxy env PATH=/tmp/g2-tool-bin:/Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:/usr/bin:/bin npm run check
  EXPECT: built in
  CWD: third_party/evenRealities-webflasher
  EVIDENCE: exit=0; 345 Node tests, zero skips; Vite production build passed; /tmp/g2-webflasher-check.log. Separately, 25 Python companion tests passed with pyserial 3.5; /tmp/g2-webflasher-python.log.

- [x] G5: official provenance and every version-specific relocation are independently reviewed
  EVIDENCE: autoreview --mode local using /Applications/ChatGPT.app/Contents/Resources/codex exited 0; no accepted/actionable findings, correctness confidence 0.94. Reviewer independently matched binaries, component hashes, anchors, hook destinations, decoder pointers, patch regions, font identity and both writer pins. Result: /tmp/g2-rebase-review.json.

- [x] G6: real Thai and stock rollback files pass the parser and final writer gate while tampered files fail
  CHECK: rtk proxy /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/check_webflasher_artifacts.mjs
  EXPECT: WEBFLASHER_ARTIFACTS_OK
  EVIDENCE: exit=0; both positive controls accepted; payload mutations and unknown whole-bundle pins rejected.

- [x] G7: the portable companion patch reproduces the working companion and both files load in the browser
  EVIDENCE: git apply succeeded on a fresh c437fdf checkout at /tmp/g2-webflasher-rebase-proof; all 12 changed files matched byte-for-byte. Browser http://127.0.0.1:3000/#firmware accepted Thai and stock 2.2.10.10 with correct hashes and Validated locally; no console errors; no device connected.
