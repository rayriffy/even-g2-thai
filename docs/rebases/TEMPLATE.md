# G2 VERSION rebase evidence

Copy this file to `VERSION.md` and [`TEMPLATE.json`](TEMPLATE.json) to
`VERSION.json` before changing the patch source.

Keep the full authenticated selection record outside the repository and put its
SHA-256 in `selection_record_sha256`. Use the literal `<empty>` for an observed
empty `mode`, `region`, or `type`; leave `null` only when it was not observed.
The gated launcher requires all fields and a 64-hex record hash.
Pass that protected file to every launcher command with `--selection-record`.

The protected JSON must use this shape; it may retain the real serial only
outside the repository:

```json
{
  "schema_version": 1,
  "target_version": "VERSION",
  "hardware_revision": "REVISION",
  "source": "owned authenticated app response",
  "captured_at": "RFC3339 timestamp",
  "device_ota_info": {
    "version": "VERSION",
    "sn": "real serial retained only in this protected file",
    "mode": "",
    "region": "",
    "type": ""
  },
  "endpoints": {
    "left_name": "Even G2_<serial>_L_<tail>",
    "right_name": "Even G2_<serial>_R_<tail>",
    "left_version": "VERSION",
    "right_version": "VERSION"
  }
}
```

The launcher parses these fields and compares them with the committed redacted
record after verifying the protected file's SHA-256.

The protected record must also include `cdn_base` and DeviceOtaInfo `subPath`,
`fileSize`, and `fileSign`. The redacted JSON's `selected_artifact` must lock
the resulting URL, size, and opaque vendor signature to the same verified stock
bundle.

```text
Target version:
Observed left/right versions:
App version/build:
APK/XAPK source, size, hash, signer:
API endpoint and query:
Authenticated DeviceOtaInfo sn/mode/region/type selection:
Hardware-variant compatibility status and evidence:
OTA metadata source and pinned commit:
Official CDN URL:
Stock size and SHA-256:
Embedded version:
Component names, sizes, CRCs, hashes:
Main component/payload offsets and size:
APP load address, preamble, file delta:
Old -> new dependency addresses:
Hook preimages and decoded stock targets:
Patched size and SHA-256:
Patched main size, programmed end, headroom:
Unchanged component proof:
Tests and verifier output:
Autoreview command and result:
Pinned G2Flash commit and stop-gate source verification:
Physical test status:
Rollback artifact and status:
```
