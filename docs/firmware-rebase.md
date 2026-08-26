# Firmware discovery and rebase playbook

This playbook records how to find and authenticate an official Even Realities
G2 firmware, move the Thai patch to that exact stock version, and prove the
rebuilt image is internally consistent before any glasses are connected.

## Read when

- the glasses report a newer firmware than `g2-thai` targets;
- Even changes the current G2 firmware or removes an older OTA from the app;
- the firmware URL, component layout, or patch addresses must be recovered;
- a rebuilt image needs an anti-brick review before device testing.

This offline procedure cannot prove physical boot or rendering.

## Non-negotiable safety boundary

1. Read the installed version from both temples before choosing a base.
2. Never flash an artifact built from an older or different stock version.
3. Keep the verified stock bundle for the installed version as the rollback
   image.
4. Do not contact the glasses while discovering, rebasing, or verifying the
   firmware.
5. Do not commit account tokens, device serials, API signing material extracted
   from the APK, captured headers, or other credentials.
6. Treat address matching as a lead. Require unique binary evidence and decoded
   Thumb-2 control flow before changing a hook.
7. A clean build, test suite, checksum pass, and autoreview are static evidence;
   physical boot, display, thermal behavior, transport, and rollback remain
   separate gates.

## Tool and repository map

- [`g2-thai`](../README.md): Thai font source, patch generator, committed patch
  specification, tests, and this playbook.
- [`g2flash`](https://github.com/jimrandomh/g2flash): EVENOTA parser,
  checksum/MRAM validation, and compiler helper. The reviewed revision for this
  playbook is
  `877c8d9490db0d3717ca012dd0f54556af3701bd`.
- [`evenRealities-openCFW`](https://github.com/kalanihelekunihi/evenRealities-openCFW):
  broader G2 firmware research and source reconstruction.
- [`Even-G2-RE`](https://github.com/lonelyobserver0/Even-G2-RE): independent app/API route research.
- [`Blutter`](https://github.com/worawit/blutter): Flutter AOT analysis; the 2.2.8 investigation used commit
  `4a60ac648bf448c5a7596437243bcd0b9376fdf0`.
- [`evenRealities-webflasher`](https://github.com/AM-Guru/evenRealities-webflasher):
  third-party digest-pinned archive and recovery tooling, not an Even service.
- [`awesome-even-realities-g2`](https://github.com/pangoleen/awesome-even-realities-g2): community project index.

## Phase 1: establish the target version

Record all of the following before downloading anything:

- left-temple firmware version;
- right-temple firmware version;
- hardware revision;
- Even app version and build number;
- date and source of each observation.

Both temples must agree. If they do not, stop and diagnose the mismatch before
building a custom image. The stock base must match the version that will receive
the patch; a similar version string is not sufficient.

A matching version is necessary but not sufficient when multiple hardware,
region, or release modes may exist. Preserve available `DeviceOtaInfo` metadata
as private provenance and never guess unknown fields. It can help authenticate
the stock bundle, but it is not a flashing gate: the Case-USB writer accepts
only the committed exact whole-bundle and Apollo-main hashes.

The phone app version and glasses firmware version are separate namespaces. In
the worked example, Android app `2.2.8` build `122` reported glasses firmware
`2.2.8.4`.

## Phase 2: find the official OTA

### Fast path: inspect the public archive metadata

Start with the WebFlasher catalog because it records original Even CDN URLs,
sizes, whole-bundle hashes, and component hashes. Pin a commit so later catalog
changes cannot silently alter the evidence.

```sh
WEBFLASHER_COMMIT=0a949409669d4efd82269515f3414925ae775cd2
TARGET_VERSION=2.2.9.22
curl -fsSL \
  "https://raw.githubusercontent.com/AM-Guru/evenRealities-webflasher/$WEBFLASHER_COMMIT/public/firmware-updates/g2/$TARGET_VERSION/metadata.json" \
  | jq '{version,sourceUrl,sourceSize,sourceSha256,components}'
```

The catalog is discovery evidence, not the final trust root. Download the
reported `sourceUrl` from the Even CDN and independently verify it.

### App path: recover the current update flow

Use this path when the target is absent from public archives or the app appears
to use a different endpoint.

#### Authenticate the APK used for analysis

The official Android package is `com.even.sg`:

- [Google Play](https://play.google.com/store/apps/details?id=com.even.sg)
- [Even Realities download support](https://support.evenrealities.com/hc/en-us/articles/14463585968399-Even-Realities-App-Download)

Prefer APK splits extracted from an owned, Play-installed copy. If a mirror is
used for static analysis, record the source, package metadata, whole-XAPK hash,
and signer certificate before trusting any recovered route. Never install the
mirror merely to inspect it.

For an XAPK or APK set:

```sh
shasum -a 256 even-realities.xapk
unzip -p even-realities.xapk manifest.json | jq .
keytool -printcert -jarfile config.arm64_v8a.apk
unzip -l config.arm64_v8a.apk | rg 'lib/arm64-v8a/libapp.so'
```

The historical input hashes and machine-specific Blutter setup are retained in
the [Even app 2.2.8 analysis record](rebases/app-2.2.8.md). They are not
expected to match a later app release.

#### Decompile the right layer

JADX is useful for Android glue such as `getAppEnv`, package information,
Android ID handling, and WebView user-agent construction. The firmware-update
client itself is Flutter AOT Dart code, so Java/Kotlin decompilation alone will
not reveal it.

Extract the arm64 Flutter libraries into one directory and run Blutter:

```sh
python3 /path/to/blutter/blutter.py /tmp/even-libs/arm64-v8a /tmp/even-blutter-out
```

Search the generated Dart assembly and pool listing for:

```text
/v2/g/check_firmware
/v2/g/check_latest_firmware
checkFirmware
downloadG2Firmware
DeviceOtaInfo
subPath
calculateSignature
```

#### Current request contract

The 2.2.8 app checks glasses firmware with:

```http
GET https://api2.evenreal.co/v2/g/check_firmware?is_ring=false
```

`check_latest_firmware` was used with `is_ring=true` for the ring path. Do not
substitute it for the glasses request without re-checking the current app.

The current glasses versions are not ordinary query parameters. They are sent
inside the URL-encoded, signed `common` header:

```text
verL=<left version>
verR=<right version>
```

Relevant request headers are:

```text
request-id
common
user-agent
token       # only when logged in
region      # only when non-empty
sign
```

The `common` map is built from app/device information followed by glasses and
locale state. Fields observed in app 2.2.8 were:

```text
platform package versionName build brand model osVersion carrier mcc mnc
buildTime appId v openUdid os sn verL verR ringSn ringVer channel
sttLanguage region sysLanguage appLanguage ts language tzName dateFmt timeFmt unit
```

Some fields are conditional. Preserve the app's insertion and encoding behavior
when comparing a capture. Do not invent or publish a real serial number.

The signature helper canonicalizes the HTTP method, path, `common` header,
optional token, sorted query parameters, and body where applicable; it sorts
the canonical pieces, joins them with newlines, computes HMAC-SHA256, and
Base64-encodes the result. The shared signing material is embedded in the app.
Do not copy it into this repository or documentation.

The read-only probe performed during the worked example moved from:

```text
403 Your device went wrong
```

without valid device headers to:

```text
401 Your login session has expired
```

with the reconstructed signed `common` header. This established the request
shape through the device-validation gate, but not authorization to retrieve
account-scoped data. A real app session token was still required and was not
captured or stored.

#### Response-to-download flow

The response model is `DeviceOtaInfo`. Fields relevant to artifact recovery
include:

```text
version subPath fileSize fileSign minAppVer mode name region sn title type
```

The app compares response `version` with the locally observed temple version.
It then asks the current CDN client to download `subPath`. Therefore:

```text
full OTA URL = selected CDN base + DeviceOtaInfo.subPath
```

App 2.2.8 contained these CDN candidates:

```text
https://cdn-az.evenrealities.com
https://cdn.evenreal.co
https://cdn-az.even-realities.com
```

The official 2.2.9.22 artifact used `https://cdn.evenreal.co`.

## Phase 3: authenticate the stock bundle

Download from the Even CDN into a versioned cache name, never directly over an
existing trusted file:

```sh
TARGET_VERSION=2.2.9.22
FW_URL='https://cdn.evenreal.co/firmware/fc250b05e98a9ff998b4b68f5f99f994.bin'
EXPECTED_SIZE=4476518
EXPECTED_SHA256='a03fbea9f68a9de6bc271daabb9f3a41c59053d1086622c76a4e990f829cc561'
STOCK=".cache/g2_$TARGET_VERSION.bin"
mkdir -p .cache
if [[ -e "$STOCK" ]]; then
  echo "$STOCK already exists; verify it separately instead of overwriting it" >&2
  exit 1
fi
CANDIDATE="$(mktemp ".cache/g2_${TARGET_VERSION}.candidate.XXXXXX")"
curl -fL "$FW_URL" -o "$CANDIDATE" || {
  echo "download failed; existing rollback files are untouched" >&2
  exit 1
}
ACTUAL_SIZE="$(stat -f '%z' "$CANDIDATE")"
ACTUAL_SHA256="$(shasum -a 256 "$CANDIDATE" | awk '{print $1}')"
if [[ "$ACTUAL_SIZE" != "$EXPECTED_SIZE" || "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]]; then
  echo "candidate verification failed; inspect then trash $CANDIDATE" >&2
  exit 1
fi
if ! ln "$CANDIDATE" "$STOCK"; then
  echo "stock path appeared during verification; candidate retained at $CANDIDATE" >&2
  exit 1
fi
strings -a "$STOCK" | rg "s200_v$TARGET_VERSION"
```

Require all of the following:

- exact whole-file size and SHA-256 from an independent metadata source;
- embedded version matching the target;
- five or six expected EVENOTA components;
- valid CRC32C in both the TOC and each component subheader;
- valid Apollo preamble length, load address, and internal CRC-32;
- Apollo programmed end below the conservative MRAM ceiling;
- no unexplained component or topology change.

Use both project verification and G2Flash's independent validator. Run the
project verifier explicitly on stock; the build runs it again on patched output:

```sh
python3 tools/verify_firmware.py ".cache/g2_$TARGET_VERSION.bin"
```

G2Flash exposes `validate_firmware` as a Python function:

```sh
TARGET_VERSION=2.2.9.22
python3 - ".cache/g2_$TARGET_VERSION.bin" <<'PY'
import importlib.util
import sys
from pathlib import Path

module_spec = importlib.util.spec_from_file_location("g2flash", "../g2flash/g2flash.py")
g2flash = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(g2flash)
g2flash.DEBUG = False
stock_path = Path(sys.argv[1])
image = stock_path.read_bytes()
segments = g2flash.validate_firmware(image)
print(stock_path, [segment["fn"] for segment in segments])
PY
```

At the pinned commit validation uses only the standard library; transport
dependencies are lazy. This exact system-Python command passed during rebase.

## Phase 4: map the new Apollo image

The patch uses installed MRAM addresses, while patch operations use offsets in
the complete OTA file. Recompute the mapping for every stock bundle.

For the main component:

```text
payload file offset = component offset + 128
installed address for payload offset p = APP_LOAD_ADDR + p - APP_PREAMBLE
file delta = APP_LOAD_ADDR - APP_PREAMBLE - payload file offset
OTA patch offset for installed address a = a - file delta
```

Current constants are:

```text
APP_LOAD_ADDR = 0x00438000
APP_PREAMBLE  = 0x20
APP_MAX_END   = 0x007F0000
```

Do not assume these survive a future architecture or bootloader change. Verify
the preamble's load address and the bootloader contract first.

## Phase 5: relocate every stock dependency

The patch depends on these semantic roles:

- two font-manager calls to the stock font-chain builder;
- the stock font-chain builder itself;
- the entry of `lv_text_encoded_letter_next_2`;
- the stock UTF-8 decoder called by the contextual wrapper;
- LVGL glyph descriptor/release routines that authenticate the IAR layout.

For each old address:

1. Convert it to an offset within the old Apollo payload.
2. Search progressively smaller instruction-aligned byte windows from the old
   function in the new payload.
3. Require one unique new match. Eight bytes can be an initial lead; prefer a
   longer exact region or multiple independent anchors.
4. Disassemble old and new regions in Thumb mode with Capstone.
5. Verify function prologue, register/field behavior, literal references, and
   return paths—not only bytes at one location.
6. Decode every relevant `BL`/`B.W` and confirm its semantic target.
7. Count direct call sites where the old research depends on caller coverage.
8. Record the old address, new address, preimage, decoded target, and evidence
   length in [`research.md`](research.md).

Do not apply one global shift. In the 2.2.9.22 rebase, different code regions
moved by `+0x3890`, `+0x6450`, and `+0xC488`.

## Phase 6: update the patch source and pins

At minimum, update:

- `build_thai.sh`: cache/output filenames, CDN URL, stock SHA-256, labels;
- `tools/generate_patch.py`: stock SHA-256, file delta, hook addresses,
  preimages, base filename, target metadata;
- `patches/thai_font.c`: target-version comment and stock delegate addresses;
- `tests/test_patch.py`: cached stock path, base hash, expected hook/delegate
  addresses;
- `README.md`, `research.md`, `flashing.md`, and this playbook;
- regenerated `patches/thai_patches.json`.

Keep strict preimages. If a hook's four stock bytes differ, generation must
fail instead of patching a nearby or guessed location.

Regenerate from source:

```sh
make patch
```

This rebuilds the font payload, preview, injected Thumb-2 code, patch
specification, output hash, and all length/checksum operations.

## Phase 7: verification gates

### Project gate

```sh
make check
git diff --check
```

The tests must cover:

- pinned font identity and expected Thai coverage;
- zero-advance combining marks;
- contextual `U+0E48..U+0E4B` mapping only before `U+0E33`;
- non-overlap of the raised tone alternatives with SARA AM;
- exact hook preimages and encoded targets;
- relocated stock delegate constants;
- removal of relocation sentinels;
- patch application to the cached stock image;
- output SHA-256 and the target-specific expected component count.

### Independent container gate

Run `g2flash.validate_firmware` on the final image. Confirm:

- component CRC32C values match payloads and subheaders;
- main preamble load address remains `0x00438000`;
- preamble low-24 length equals the staged main payload size;
- internal zlib CRC-32 is current;
- programmed end remains at or below `0x007F0000`.

### Component identity gate

Hash stock and patched component payloads independently. For this patch, only
`ota/s200_firmware_ota.bin` may change. Codec, BLE, touch, case, and Apollo
bootloader payloads must remain byte-identical to stock.

### Final control-flow gate

Disassemble the final output, not only the compiler's temporary blob:

- both font-chain hooks must `BL` the injected chain wrapper;
- the text-helper entry must `B.W` the contextual wrapper;
- the chain wrapper must construct and call the relocated stock chain-builder
  Thumb address;
- the text wrapper must construct and call the relocated stock UTF-8 Thumb
  address;
- no hook may branch into font data, padding, or beyond the staged payload.

### Version and artifact gate

Record the final filename, exact size, SHA-256, embedded version, main payload
size, programmed end, ceiling headroom, component hashes, and test output.

### Structured review gate

Run autoreview after the build and tests are frozen:

```sh
autoreview --mode local
```

If `codex` is not on `PATH`, pass the installed CLI explicitly:

```sh
autoreview --mode local --codex-bin /absolute/path/to/codex
```

Ask the reviewer specifically about stock provenance, file/MRAM mapping, hook
preimages and targets, delegate addresses, append bounds, preamble/component
checksums, generated-spec consistency, tests, rollback, and claims that exceed
static evidence. Verify every reported finding against the real binary.

## Phase 8: physical test and rollback boundary

Only after all offline gates pass, follow [`flashing.md`](flashing.md).

Case-USB WebFlasher is the only supported writer. `g2flash` remains a pinned
compiler helper; direct BLE transport, discovery, flashing, and rollback are
retired from this project.

- Keep both the stock and patched images.
- Do not factory-reset or forget/unpair the glasses or R1 ring.
- Flash one temple first while the other remains a working reference.
- Verify ordinary stock screens before Thai strings.
- Test `ภาษาไทย`, `กรุงเทพมหานคร`, `น้ำ`, and `เก่ง`.
- Roll back with the verified stock image for the same version if any boot,
  display, interaction, battery, or thermal behavior is abnormal.

## Worked examples

- [G2 2.2.8.4 rebase evidence](rebases/2.2.8.4.md)
- [G2 2.2.9.22 rebase evidence](rebases/2.2.9.22.md)

## Evidence record template for the next version

Copy [`rebases/TEMPLATE.md`](rebases/TEMPLATE.md) and
[`rebases/TEMPLATE.json`](rebases/TEMPLATE.json) before editing code. Record
the Case-USB writer pin and physical-test evidence alongside the artifact.
