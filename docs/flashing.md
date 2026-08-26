# Flashing and rollback

This project writes firmware only through the vendored WebFlasher Case-USB
route. Do not use `g2flash.py`, direct BLE flashing, or an automatic stock
recovery panel for the Thai artifact.

## 1. Build and verify

```sh
cd /Users/rayriffy/Git/g2-thai
PATH="$PWD/.venv/bin:$PATH" make check
make webflasher
```

Keep both images:

```text
.cache/g2_2.2.9.22.bin
build/g2_2.2.9.22_thai.bin
```

`make webflasher` verifies that the exact whole-bundle and Apollo-main hashes
are present in the Case-USB writer. A mismatched file cannot be selected for a
write.

## 2. Prepare the Case-USB writer

```sh
make webflasher-serve
```

This initializes the pinned WebFlasher submodule, applies the local Thai pin,
installs its `package-lock.json` dependencies, and serves
`http://127.0.0.1:3000`.

Charge the Case and Mac, connect the Case with a USB-C data cable, and seat
both temples. Keep the Case, cable, temples, and browser tab still throughout
the operation. Do not factory-reset or unpair the glasses or R1 ring.

## 3. Flash one lens first

In WebFlasher, choose the local `build/g2_2.2.9.22_thai.bin` file. It must
show **Validated locally** and the exact Thai Case-USB-only pin.

Open **Advanced Mode → Recovery Console → Running-temple recovery through the
Case**. Never use **Recover with update over USB**: that automatic panel selects
the official stock catalog image.

Choose one temple, confirm it is seated, acknowledge the single-slot risk, and
type `FLASH GLASSES FIRMWARE`. Keep the write button as an explicit operator
action.

After a successful audit, confirm the Even app reconnects, double-tap the
dimple repeatedly to prove the dashboard does not reboot, then test:

```text
ภาษาไทย
กรุงเทพมหานคร
น้ำ
เก่ง
```

Only after these checks pass should the other temple be flashed. The patched
firmware intentionally reports stock version `2.2.9.22`, so version liveness
does not distinguish the Thai build; dashboard and rendering checks do.

## Rollback

Use the same manual Case recovery panel with `.cache/g2_2.2.9.22.bin`, one
temple at a time. The retained stock bundle is the deterministic rollback
artifact.

Offline checks prove container integrity and writer pins only. They cannot
prove boot, display quality, thermal behavior, or recovery on physical glasses.
