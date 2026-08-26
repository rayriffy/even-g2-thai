# G2 VERSION rebase evidence

Copy this file to `VERSION.md` and [`TEMPLATE.json`](TEMPLATE.json) to
`VERSION.json` before changing the patch source.

Record public OTA metadata only as firmware provenance. The writer is the
vendored Case-USB WebFlasher: its exact whole-bundle and Apollo-main pins, plus
the physical test result, are the flashing evidence. Never add serials, app
tokens, or other private device data to this repository.

```text
Target version:
App version/build and APK/XAPK source:
OTA metadata source and pinned commit:
Official CDN URL:
Stock size and SHA-256:
Embedded version:
Component names, sizes, CRCs, hashes:
Main component/payload offsets and size:
APP load address, preamble, file delta:
Old -> new dependency addresses:
Hook preimages and decoded stock targets:
Font source, SHA-256, and redistribution status:
Patched size and SHA-256:
Patched main size, programmed end, headroom:
Unchanged component proof:
Firmware test and verifier output:
Case-USB writer whole-bundle/main pin:
WebFlasher test and production-build output:
Physical one-lens test status:
Rollback artifact and status:
```
