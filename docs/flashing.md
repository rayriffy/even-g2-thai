# Flashing and rollback

Flashing custom firmware can permanently brick either lens. Complete the
offline build and keep the verified stock image before connecting.

## 1. Build and verify

```sh
make check
```

Keep both files:

```text
.cache/g2_2.2.6.10.bin
build/g2_2.2.6.10_thai.bin
```

## 2. Prepare G2Flash

```sh
cd /Users/rayriffy/Git/g2flash
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

Find the CoreBluetooth UUID for each arm:

```sh
./venv/bin/python - <<'PY'
import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover(timeout=20, return_adv=True)
    for address, (device, advertisement) in devices.items():
        name = advertisement.local_name or device.name or ""
        if "G2_" in name:
            print(name, address)

asyncio.run(main())
PY
```

The names contain `_L_` and `_R_`; copy their corresponding UUIDs as
`LEFT_UUID` and `RIGHT_UUID`. The current G2Flash parser requires both values;
`g2://local` alone is not accepted.

## 3. Prove transport without starting OTA

Run from `/Users/rayriffy/Git/g2flash`:

```sh
./venv/bin/python g2flash.py \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f /Users/rayriffy/Git/g2-thai/build/g2_2.2.6.10_thai.bin \
  --lens both \
  --stop-before file_check
```

Type the warranty phrase when prompted. This gate connects and enables BLE
notifications but stops before OTA BEGIN, FILE_CHECK, or firmware data. Do not
use `--stop-before flash` as a no-write test: in the current G2Flash state
machine it already sends OTA BEGIN and FILE_CHECK before stopping.

Do not proceed unless both sides report discovery success and
`stopping before FILE_CHECK`.

## 4. Flash explicitly

Start with one lens so the other remains a working reference:

```sh
./venv/bin/python g2flash.py \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f /Users/rayriffy/Git/g2-thai/build/g2_2.2.6.10_thai.bin \
  --lens left
```

After boot, exercise ordinary stock screens first. Then test Thai strings such
as `ภาษาไทย`, `กรุงเทพมหานคร`, `น้ำ`, and `เก่ง`. Confirm that the tone and
nikhahit in `น้ำ` are separated. Then flash the right lens:

```sh
./venv/bin/python g2flash.py \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f /Users/rayriffy/Git/g2-thai/build/g2_2.2.6.10_thai.bin \
  --lens right
```

Do not close Terminal, suspend the Mac, power off an arm, or restart the Even
app during a write. G2Flash retries whole components after explicit failures;
do not manually restart it while a transfer is active.

## Rollback

Flash the verified stock image with the same connection string, one lens at a
time:

```sh
./venv/bin/python g2flash.py \
  -c 'g2://local?left=LEFT_UUID&right=RIGHT_UUID&addressType=random' \
  -f /Users/rayriffy/Git/g2-thai/.cache/g2_2.2.6.10.bin \
  --lens left
```

Repeat with `--lens right`. A newer official Even OTA should also replace the
modified main app, but the locally retained stock image is the deterministic
rollback artifact.

This project verifies container integrity offline. It cannot prove boot,
display quality, thermal behavior, or recovery without the physical glasses.
