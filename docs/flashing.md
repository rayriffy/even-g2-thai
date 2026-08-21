# Flashing and rollback

Flashing custom firmware can permanently brick either lens. Complete the
offline build and keep the verified stock image before connecting.
If this target version has not already been authenticated and rebased, stop and
complete the [firmware discovery and rebase playbook](firmware-rebase.md)
first.

Current block: the [2.2.9.22 evidence record](rebases/2.2.9.22.md) does not yet
authenticate the device-specific `mode`/`region`/`type` selection. Do not run
the transport or flashing sections below until that compatibility gate is
closed and recorded.

## 1. Build and verify

```sh
make check
```

Keep both files:

```text
.cache/g2_2.2.9.22.bin
build/g2_2.2.9.22_thai.bin
```

## 2. Prepare G2Flash

These commands and the no-OTA stop boundary are reviewed against G2Flash
commit `877c8d9490db0d3717ca012dd0f54556af3701bd`. Do not use another revision
without re-reading its stage ordering and updating the playbook evidence.

```sh
set -euo pipefail
cd /Users/rayriffy/Git/g2flash
G2FLASH_COMMIT=877c8d9490db0d3717ca012dd0f54556af3701bd
g2flash_dirty="$(git status --porcelain --untracked-files=all | sed '/^?? \.DS_Store$/d')"
test -z "$g2flash_dirty" || {
  echo "G2Flash has local source changes; use a fresh clean checkout" >&2
  exit 1
}
git checkout --detach "$G2FLASH_COMMIT"
test "$(git rev-parse HEAD)" = "$G2FLASH_COMMIT" || {
  echo "G2Flash checkout is not pinned to $G2FLASH_COMMIT" >&2
  exit 1
}
g2flash_dirty="$(git status --porcelain --untracked-files=all | sed '/^?? \.DS_Store$/d')"
test -z "$g2flash_dirty" || {
  echo "G2Flash has local source changes; use a fresh clean checkout" >&2
  exit 1
}
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt
```

Charge both arms and the Mac. Quit the Even app and disable Bluetooth on the
paired phone so both arms advertise. Keep the Mac awake throughout the flash.
The first scan from Terminal will request macOS Bluetooth permission.

Do **not** factory-reset the glasses, forget/unpair them from the phone, or
remove the R1 ring pairing before flashing. G2Flash needs the phone connection
to be temporarily inactive, not deleted. The patched main app ends below
`0x007F0000`; persistent Cordio pairing records begin at `0x007FF000`, outside
the programmed OTA range. Leave the R1 paired. If an arm does not advertise,
first close the Even app, disable the phone's Bluetooth, and wake the glasses;
do not use a reset as the discovery fix.

UUID discovery is also gated because it touches the Bluetooth adapter. Run it
only after the compatibility record is verified:

```sh
python3 tools/gated_g2flash.py --g2flash-root ../g2flash \
  --operation discover \
  --selection-record /secure/path/to/device-ota-info.json
```

The names contain `_L_` and `_R_`; copy their corresponding UUIDs as
`LEFT_UUID` and `RIGHT_UUID`. The current G2Flash parser requires both values;
`g2://local` alone is not accepted.

## 3. Prove transport without starting OTA

Run from `/Users/rayriffy/Git/g2-thai`. The launcher checks the redacted
compatibility record, exact stock/patched hash, G2Flash commit and cleanliness,
and its virtualenv before it can connect:

```sh
python3 tools/gated_g2flash.py --g2flash-root ../g2flash \
  --operation transport \
  --selection-record /secure/path/to/device-ota-info.json -- \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f build/g2_2.2.9.22_thai.bin \
  --lens both \
  --stop-before file_check
```

Type the warranty phrase when prompted. This gate connects and enables BLE
notifications, including GATT/CCCD writes, but stops before OTA BEGIN,
FILE_CHECK, or firmware data. It is a no-OTA gate, not a write-free device
interaction. Do not use `--stop-before flash` as a no-OTA test: in the current
G2Flash state machine it already sends OTA BEGIN and FILE_CHECK before stopping.
This claim is version-specific to the pinned G2Flash commit above; verify the
source again before changing that pin.

Do not proceed unless both sides report discovery success and
`stopping before FILE_CHECK`.

## 4. Flash explicitly

Start with one lens so the other remains a working reference:

```sh
python3 tools/gated_g2flash.py --g2flash-root ../g2flash \
  --operation flash \
  --selection-record /secure/path/to/device-ota-info.json -- \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f build/g2_2.2.9.22_thai.bin \
  --lens left
```

After boot, exercise ordinary stock screens first. Then test Thai strings such
as `ภาษาไทย`, `กรุงเทพมหานคร`, `น้ำ`, and `เก่ง`. Confirm that the tone and
nikhahit in `น้ำ` are separated. Then flash the right lens:

```sh
python3 tools/gated_g2flash.py --g2flash-root ../g2flash \
  --operation flash \
  --selection-record /secure/path/to/device-ota-info.json -- \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f build/g2_2.2.9.22_thai.bin \
  --lens right
```

Do not close Terminal, suspend the Mac, power off an arm, or restart the Even
app during a write. G2Flash retries whole components after explicit failures;
do not manually restart it while a transfer is active.

## Rollback

Flash the verified stock image with the same connection string, one lens at a
time:

```sh
python3 tools/gated_g2flash.py --g2flash-root ../g2flash \
  --operation rollback \
  --selection-record /secure/path/to/device-ota-info.json -- \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f .cache/g2_2.2.9.22.bin \
  --lens left
```

Repeat with `--lens right`. A newer official Even OTA should also replace the
modified main app, but the locally retained stock image is the deterministic
rollback artifact.

This project verifies container integrity offline. It cannot prove boot,
display quality, thermal behavior, or recovery without the physical glasses.
