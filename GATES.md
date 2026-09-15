# Gates: Thai rendering performance on 2.2.10.10

OWNS: patches/thai*, tools/*, tests/*, docs/*, README.md, GATES.md, patches/webflasher_case_usb_thai.patch, third_party/evenRealities-webflasher/src/lib/localTempleFlashTargets.js

Scope: decompile authenticated stock font paths, reduce Thai rendering CPU work, preserve shaping and buffer ownership, rebuild and validate a local candidate.

- [x] G1: Stock disassembly and reconstructed control flow explain the optimization and its limits
  EVIDENCE: SHA-pinned Thumb listing plus reconstructed descriptor/bitmap/release control flow in docs/thai-performance.md; XIP font-bank and hardware boundaries explicit.
- [x] G2: Rebuilt firmware passes all regression and emulation checks
  CHECK: rtk proxy env PATH=/Users/rayriffy/Git/g2-thai/.venv/bin:/usr/bin:/bin:/usr/sbin:/sbin make check
  EXPECT: OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=4af54b6b8371bfcd8db0b2e6e4c6e4449585f7ba221e5807d3354c97926bab20; exit=0; EXPECT=matched; output-sha256=497ffd48860aaa3559c7f119fe212a7e7ae04fb0b8a10df87f17cd37707a9780; output-bytes=8260; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=8bc73469e98a/21 entries
- [x] G3: Deterministic artifact benchmark demonstrates reduced lookup and bitmap instruction counts
  CHECK: rtk proxy .venv/bin/python tools/benchmark_thai.py --baseline build/perf-baseline --output build/thai-performance.json
  EXPECT: PERFORMANCE_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=d2a54af17112ecff2a8200c51ee02cd5cb61479103c34790680a39e1cf29c354; exit=0; EXPECT=matched; output-sha256=fe3e83686d341792283e1f954ee2cae5af54a3799b39d86397f7929ae7dc5ec2; output-bytes=171; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=8bc73469e98a/21 entries
- [x] G4: WebFlasher exact pins accept the candidate and rollback and reject mutations
  CHECK: rtk proxy /Users/rayriffy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node tools/check_webflasher_artifacts.mjs
  EXPECT: WEBFLASHER_ARTIFACTS_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=23c940328866e8961b6beb911d5d025f956204c95828660b43dba90ed0a060c3; exit=0; EXPECT=matched; output-sha256=de63f7b8fd20d1fe45f27de917ff2ee4849c38239bfbadb67a3aa3cd7d5a6d17; output-bytes=182; shell=/bin/sh; cwd=/Users/rayriffy/Git/g2-thai; path=8bc73469e98a/21 entries
- [x] G5: Final diff, generated artifact reproducibility, and documentation agree
  EVIDENCE: Fresh compile byte-matches patch spec; candidate SHA-256 92ba54d4203e97e426425385eec98af8aeb801d0faacb95c2e54ab9b3308452f; pinned G2Flash validates both six-component bundles; portable companion patch reproduces all 12 files; 158 relevant companion tests and Vite build pass; git diff --check clean. Semantic scan reviewed with no actionable findings; assembly-only call edge verified by artifact emulation. Docs state hardware and native-bank limits.

Hardware boundary: no flashing requested. Actual frame rate, GPU timing, boot and rollback require physical validation; offline instruction counts do not establish FPS parity.
Discovery: indexed symbol search `thai` located patches/thai_font.c callbacks and emulator tests; affected-test graph found test_patch.py and test_rebase.py. Binary-dispatched emulation coverage is checked explicitly too.
