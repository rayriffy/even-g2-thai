---
read_when: Updating login, signing, firmware request fields, or CDN URL resolution.
---

# Protocol evidence

Recovered statically from `Even+Realities_2.4.0_APKPure.xapk`:

- Package: `com.even.sg`, version `2.4.0`, build `246`.
- XAPK SHA-256: `0e65021438f27d7912964e365310bf414b85d5d46826f355032a2e0489c30feb`.
- ARM64 `libapp.so` SHA-256: `931fc100cd061402c2d91c6c4d9d1f1acb2fa07d1fe85d4d0e7a43633cf3f3a8`.
- Dart: `3.11.5`, compressed pointers; snapshot `78da37fed6bf1489361a312568249f3f`.

REA identified the archives and ELF. Its Android provider lacked the required
JADX JAR, and its Hopper bridge timed out. Dart objects and annotated ARM64
instructions were subsequently recovered using
[Blutter](https://github.com/worawit/blutter). Generated analysis and temporary
build tools live outside this project under `/tmp/even-apk-2.4.0-analysis`.

Addresses below are virtual addresses in this exact ARM64 library.

| Dart method | Address | Observation |
| --- | --- | --- |
| `ApiServiceLoginExt.login` | `0x2466a90` | POST `/v2/g/login`, JSON keys `email`, `passwd` |
| `LoginPwdPublicMethod.login` | `0x2466110` | Calls `EncryptExt.encodePwd` before login |
| `EncryptExt.encodePwd` | `0x23e17a8` | Base64 of AES-CBC encrypted UTF-8 password |
| `EncryptExt.key` | `0x2409628` | UTF-8 bytes of the 32-character ASCII key configured locally |
| `EncryptExt.iv` | `0x2409524` | Bytes 1 through 16; Dart small integers are tagged |
| `encryptAesCbc` / `PaddedBlockCipher` | `0x23e1838` / `0x23e2250` | AES/CBC/PKCS7 |
| `ApiServiceCommonExt._checkFirmwareSource` | `0x2333a94` | GET `/v2/g/check_firmware`, query `is_ring=false` for glasses or `true` for R1 |
| `GlassesEvenApiAuthenticator.authenticate` | `0x191e140` | Headers `common`, `request-id`, `user-agent`, `sign`; adds `token` and `region` after login |
| `GlassesEvenApiAuthenticator._buildCommon` | `0x19207f8` | G2: `verL`, `verR`, `sn`; R1: `ringVer`, `ringSn`; UTC ISO timestamp `ts` |
| `GlassesEvenApiAuthenticator._encodeCommonHeader` | `0x1921810` | Ordered `key=encodeQueryComponent(value)` pairs joined with `&` |
| `SignatureUtil.calculateSignature` | `0x191ebd4` | Sort string components, join with LF, HMAC-SHA256, standard Base64 |
| `AppEnv.toHeader` / `AppEnv.fromJson` | `0x1923a48` / `0x20d000c` | Android app fields, `appId=1001`, `v=3` |
| `UserInfo` serializer | `0x1a5785c` | Account operating region is `opRegion` |
| `DeviceOtaInfo` serializers | `0x182e30c` / `0x211e914` | Firmware `version`, `subPath`, `fileSize`, `fileSign` |
| `CheckUpdateController.downloadFirmwareFile` | `0x26f7e10` | Resolve `subPath` against the active CDN origin |

In Android 2.4.0, `authenticate` at `0x191e2cc..0x191e324` checks the token's
length before adding both `token` and `region`. There is no separate region
length check: an empty account `opRegion` is still sent and included in `common`.
The older 2.2.8 notes in the rebase playbook describe a different observed
contract. The current client follows the supplied 2.4.0 APK.

Signature components:

1. Uppercase HTTP method, URI path without the query, exact `common` header.
2. Nonempty account token, when present.
3. Nonempty query: sort keys, join decoded `key=value` strings with `&`.
4. Exact nonempty JSON body for POST/PUT/PATCH.

Sort all components lexicographically; join with `\n` without a trailing LF.
The HMAC key is the UTF-8/ASCII text shipped in the library, not hex-decoded.
The password AES key is likewise ASCII text, not hex-decoded.
Extracted key values are intentionally omitted from this repository. Configure
them through the ignored `.cache/even-api.json` file or environment variables;
see the [setup guide](firmware-download.md). Tests use synthetic keys.
The client performs AES-256-CBC/PKCS7 in-process through CommonCrypto on macOS
or OpenSSL's EVP API on Linux; no password or key is passed to a child process.

Recovered CDN candidates, in order:
`https://cdn-az.evenrealities.com`, `https://cdn.evenreal.co`,
`https://cdn-az.even-realities.com`.
Resolved firmware links are limited to these HTTPS hosts, without userinfo or
nonstandard ports, including when `subPath` is an absolute URL.

The phone model, device ID, locale, and user agent in the script are synthetic
request defaults. They were not captured from a running phone. The supplied
G2 firmware version is set identically for both legs, matching the app's G2
recovery projection when versions differ. R1 mode instead sends `ringVer` and
optional `ringSn`, without G2 device fields. The ring version falls back to
`0.0.0` in the APK at `0x1920e80`; the script uses that placeholder when an R1
installed version is not supplied. No test-firmware requests are made.

The request contains the installed version, not a desired target version.
`--firmware-version` (alias `--expected-version`) validates the offered metadata
locally. It cannot select an arbitrary version from the server.

Verification: independent Apple CommonCrypto AES vectors (ASCII, Unicode,
block-aligned plaintext), deterministic signature vector, and a loopback HTTP
fixture exercising the CLI's login -> region/token -> signed GET -> URL flow
for both G2 and R1, including custom target matching and legacy CLI compatibility.
An unauthenticated production check on 2026-10-29 reached the API and returned
JSON business code `401` (`Your login session has expired`). This does not
establish successful authenticated signing or that 2.4.0.24 is offered to a
particular account. No real account credentials were available during testing.

Saved login is a local script feature, independent of the APK protocol.
`even_credentials.py` calls Apple's `SecItemAdd`, `SecItemCopyMatching`,
`SecItemUpdate`, and `SecItemDelete` through `ctypes` and CoreFoundation.
Reference: [Apple Security SecItem declarations](https://github.com/apple-oss-distributions/security/blob/main/keychain/headers/SecItem.h).
The generic-password item service includes the API origin; its secret data
contains email, password, token, region, and device ID. The first save requires
`--save-login`; later runs reuse the session for either device. Only a saved
session rejected with HTTP/API code 401 triggers a single automatic login.
Native Keychain CRUD is verified with an isolated, generated test service and
synthetic credentials; the test removes its entry afterward. Production account
authentication remains unverified.
