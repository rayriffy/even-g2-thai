---
read_when:
  - Resolving public G2 or R1 firmware URLs or managing a saved Even login.
---

# Even G2 / R1 firmware URL

By default, `even_firmware.py` logs into Even, reports installed firmware
**2.3.2.14** for both glasses legs, and prints the URL offered for **2.4.0.24**.
Python 3.9+; no pip dependencies. Password encryption runs in-process using
CommonCrypto on macOS or OpenSSL `libcrypto` (3 or 1.1) on Linux. Passwords and
app keys are never passed to a child process.

Before the first request in a fresh checkout, configure the app constants
recovered from your APK in the ignored local file `.cache/even-api.json`:

```json
{
  "signing_key": "EXTRACTED_SIGNING_KEY_ASCII",
  "password_key": "EXTRACTED_32_BYTE_AES_KEY_ASCII"
}
```

Keep that file private (`chmod 600 .cache/even-api.json`). The equivalent
environment variables are `EVEN_API_SIGNING_KEY` and `EVEN_API_PASSWORD_KEY`;
environment values override the file. Both are ASCII key text, not hex-decoded
bytes. See the [APK method locations](protocol.md) for recovery evidence.
Extracted constants, account credentials and tokens must not be committed.
`--help`, `--dry-run` and `--forget-login` work without app configuration.
Tests use synthetic public keys and need no extracted material.

```sh
python3 even_firmware.py --email you@example.com --serial YOUR_G2_SERIAL
```

Enter your Even account password at the hidden prompt. Find the glasses serial
in the Even app's device information. Serial is optional, but supplying the real
G2 serial reproduces a connected device's request more closely.

On macOS, save your login once in Keychain:

```sh
python3 even_firmware.py --save-login --email you@example.com --serial YOUR_G2_SERIAL

# Subsequent G2 or R1 checks reuse the saved session, without email/password input.
python3 even_firmware.py --serial YOUR_G2_SERIAL
python3 even_firmware.py --r1 --serial YOUR_R1_SERIAL

# Remove the saved login, or bypass it for one invocation.
python3 even_firmware.py --forget-login
python3 even_firmware.py --no-saved-login --email you@example.com
```

`--save-login` performs a fresh password login and saves the email, password,
token, account region, and device ID after successful authentication. Later runs
reuse the token; an expired saved token triggers one password login and token
update. Failed password logins are not retried. Run `--save-login` again to
replace a password. macOS may show a Keychain access dialog.

Storage uses the native Keychain APIs, without passing secrets through process
arguments or writing a credentials file. One profile is kept per API origin and
shared by G2/R1. Saving another account replaces that origin's profile; specifying
a different `--email` skips the saved credentials. `--forget-login --api-base URL`
removes only that origin's profile. Saved-login support requires macOS; the
interactive and environment-variable workflows remain available elsewhere.

The URL goes to stdout; version/size go to stderr. To include mirror URLs,
file size, and the server's `fileSign`:

```sh
python3 even_firmware.py --email you@example.com --serial YOUR_G2_SERIAL --json
```

Other options:

```sh
# Inspect the request without logging in or using the network.
python3 even_firmware.py --dry-run

# Override the installed and target versions.
python3 even_firmware.py --current-version 2.3.2.14 --firmware-version 2.4.0.24

# Query R1 ring firmware instead of G2 glasses.
python3 even_firmware.py --r1 --email you@example.com --serial YOUR_R1_SERIAL --json

# Require a particular R1 target, supplying the ring's actual installed version.
python3 even_firmware.py --r1 --current-version YOUR_R1_VERSION --firmware-version TARGET_R1_VERSION

# Firmware-client tests from the repository root.
python3 -m unittest discover -s tests -p 'test_even*.py' -v

# Also test a temporary native Keychain item (created and removed by the test).
EVEN_TEST_KEYCHAIN=1 python3 -m unittest discover -s tests -p 'test_even*.py' -v
```

For account automation, environment variables: `EVEN_EMAIL`, `EVEN_PASSWORD`,
`EVEN_GLASSES_SN`, `EVEN_RING_SN`, `EVEN_REGION`, `EVEN_TOKEN`. An existing `EVEN_TOKEN` skips
login; pair it with the account's `EVEN_REGION` (`user.opRegion` in the login
response). Normal login infers that region automatically. `EVEN_TOKEN` bypasses
Keychain and is not renewed automatically. `EVEN_PASSWORD` overrides a saved
password/token. Passwords and tokens are never printed; persistence requires an
initial `--save-login`. `--dry-run` neither accesses Keychain nor uses the network.

The default API is `https://api.evenrealities.com`; `--api-base` accepts another
HTTPS origin. The APK also lists `https://api2.evenreal.co` and
`https://api.even-realities.com` as production alternatives. TLS verification
remains enabled; API redirects are rejected.

`--r1` selects the ring for this invocation: `--serial` and `--current-version`
then describe the R1. Its serial defaults to `EVEN_RING_SN`; the G2 serial is
never reused. With no installed version supplied, R1 sends the app's unknown
version placeholder `0.0.0`. R1 accepts whatever target the server offers unless
`--firmware-version` is specified. G2 retains defaults `2.3.2.14` / `2.4.0.24`.
Run once per device to resolve both firmware URLs.

The script queries the public firmware endpoint. Account rollout, serial, and
region can affect the offered version. `--firmware-version` requires the returned
version to match; it does not make the server offer an arbitrary historical or
unreleased version. A mismatch fails without printing a download URL.
`--expected-version` remains an alias. An empty `--firmware-version ''` accepts
whatever version the server offers. `fileSign` is retained verbatim; its checksum
algorithm has not been established here.

Returned URLs must use HTTPS on one of the three recovered Even CDN hosts;
other hosts, userinfo and nonstandard ports are rejected. The script resolves
URLs only. It does not download or flash firmware.
Authenticated production login and the availability of 2.4.0.24 still require
verification with your account. See [protocol evidence](protocol.md).

`make test` discovers these tests alongside the firmware patch tests. The URL
client, API configuration, crypto and Keychain helpers live at the repository root; the APK and generated
reverse-engineering output are not required to run either the client or its tests.
