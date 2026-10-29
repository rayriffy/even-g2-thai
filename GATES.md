# Gates: G2 Thai firmware 2.4.0.24 rebase

OWNS: build_thai.sh, patches/thai*, patches/webflasher_case_usb_thai.patch, tools/*, tests/*, docs/*, docs/rebases/*, README.md, GATES.md, third_party/evenRealities-webflasher/src/lib/localTempleFlashTargets.js, third_party/evenRealities-webflasher/tests/firmware.test.mjs, third_party/evenRealities-webflasher/README.md

Scope: authenticate the supplied stock OTA, relocate every firmware dependency, preserve Maitree coverage/shaping, rebuild and validate the candidate and local Case-USB pins, commit and push.

- [x] G1: Stock metadata, unique anchors, boundaries, final hooks, component preservation and all Thai regression/emulation checks pass
  CHECK: rtk proxy env PATH=/Users/rayriffy/Git/g2-thai/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin G2FLASH_ROOT=/tmp/g2flash-24024 make check
  EXPECT: /^OK$/m
  EVIDENCE: automatic-evidence=v1; definition-sha256=23e563bda7d5a360cc3e5c4f249496f3e6cef96415bb0d778b6fef3bf7f8d8e3; exit=0; EXPECT=matched; output-sha256=2abd640aca76f981ca084aee431abe3aba47fd43fc5e72a1e18f397304a65280; output-bytes=12574; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G2: Final local candidate and same-version stock rollback pass real parser/writer gates and tamper rejection
  CHECK: rtk proxy /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/check_webflasher_artifacts.mjs
  EXPECT: WEBFLASHER_ARTIFACTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=23c940328866e8961b6beb911d5d025f956204c95828660b43dba90ed0a060c3; exit=0; EXPECT=matched; output-sha256=2f7da5d1e5edc9333019b8a57a6d702057425f20fc03c3478d91be59cf22172a; output-bytes=180; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=a97ba71f236f/22 entries
- [x] G3: Independent stock/candidate validation, portable companion patch, companion tests/build and archive inputs verified
  EVIDENCE: Pinned G2Flash validates stock/candidate with its original ceiling; 345 companion JS tests, 25 companion Python tests and Vite build pass. Portable patch applies to clean c437fdf and reproduces all 12 changed files. Source regeneration matches the committed spec byte-for-byte. Archive helper resolves 2.4.0.24 paths and renders the embedded font; seven archive files verified after extraction. Docs local links and four final Thumb branch targets checked independently.
- [x] G4: Versioned investigation and listings complete; structured review has no actionable findings
  EVIDENCE: Versioned JSON, three SHA-pinned Thumb listings and investigation report complete; local documentation links pass. Structured autoreview with account-listed gpt-5.6-sol reports zero findings and patch is correct (0.97 confidence). Full report retained at build/rebase-2.4.0.24-autoreview.json.
- [x] G5: Scoped Conventional Commit pushed; remote commit matches local
  EVIDENCE: Source commit 25df4a9079cb151c42dac6ccf4ba13d5f852345d (feat(patches): rebase Thai font to firmware 2.4.0.24) pushed to main; git ls-remote confirmed that exact SHA. HTTPS push rejected the varkaria identity; ssh -T authenticated rayriffy and the explicit SSH push succeeded. Saved HTTPS remote unchanged. Final verification ledger is committed separately.

Discovery: indexed symbol query `rebase` returned tests/test_rebase.py and docs/firmware-rebase.md. TraceDecay identified generator and tests; stale-index warnings require exact native file verification. Initial unrelated changes: .DS_Store, untracked third_party/ZF#2ndPixelus.ttf, pre-existing local WebFlasher patch. Preserve all.
Hardware boundary: offline investigation/rebase only; physical flash, boot, rendering and rollback untested.
