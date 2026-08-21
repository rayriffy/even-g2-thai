# Even app 2.2.8 firmware-update evidence

This record identifies the Android/Flutter input used to recover the update
contract documented in the
[firmware discovery and rebase playbook](../firmware-rebase.md).

## Static-analysis input

```text
Package: com.even.sg
Version name: 2.2.8
Version code/build: 122
XAPK size: 336,194,024 bytes
XAPK SHA-256: 4b9fd9e8b1a6b7ade6499582547cd650aaa05319cec485628c1016f606c624fc
Signer SHA-1: 4b7c88acf4ab977fdb7361937e5a3f90eef56468
libapp.so SHA-256: 61417582f5cb0dde72e3439fc6c9ced89f63f0238d1f0e2853ee1d9ef899efca
```

The mirror copy was used only for static inspection. The package identity was
cross-checked against Google Play, and the APK signer matched the mirror's
published certificate. This does not make the mirror an official distribution
channel.

## Blutter setup used

Blutter commit:

```text
4a60ac648bf448c5a7596437243bcd0b9376fdf0
```

On the Apple Silicon analysis host, the successful invocation needed Homebrew
ICU and Capstone paths:

```sh
env \
  PKG_CONFIG_PATH='/opt/homebrew/opt/icu4c@78/lib/pkgconfig:/opt/homebrew/opt/capstone/lib/pkgconfig' \
  CMAKE_PREFIX_PATH='/opt/homebrew/opt/icu4c@78:/opt/homebrew/opt/capstone' \
  /tmp/blutter-venv/bin/python blutter.py \
  /tmp/even-libs/arm64-v8a /tmp/even-blutter-out
```

Blutter identified Dart `3.11.5` and generated `pp.txt` plus per-library
assembly under `/tmp/even-blutter-out`.

## Authentication boundary

The recovered signed glasses request progressed from `403 Your device went
wrong` without valid device headers to `401 Your login session has expired`
with the reconstructed `common` header and signature. No login token, device
serial, or embedded API signing material was retained.
