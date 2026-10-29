#!/usr/bin/env python3
"""Log into Even and resolve the public G2 or R1 firmware download URL.

Protocol recovered from Even Android 2.4.0 (246). Python 3.9+ on macOS/Linux.
"""

import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid

from even_credentials import CredentialStore, CredentialStoreError
from even_api_config import ApiConfigError, load_api_keys
from even_crypto import CryptoError, encrypt_aes_cbc


API_BASE = "https://api.evenrealities.com"
CDN_BASES = (
    "https://cdn-az.evenrealities.com",
    "https://cdn.evenreal.co",
    "https://cdn-az.even-realities.com",
)
PASSWORD_IV = bytes(range(1, 17))


class EvenError(Exception):
    """A user-readable protocol or transport error."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def encode_password(password):
    """Encrypt UTF-8 using AES-256-CBC/PKCS7, then standard Base64."""
    _, password_key = load_api_keys()
    encrypted = encrypt_aes_cbc(password.encode("utf-8"), password_key, PASSWORD_IV)
    return base64.b64encode(encrypted).decode("ascii")


def signature(method, path, common, query=None, body="", token=""):
    """SignatureUtil.calculateSignature at libapp.so 0x191ebd4."""
    signing_key, _ = load_api_keys()
    parts = [method, path, common]
    if token:
        parts.append(token)
    if query:
        parts.append("&".join(f"{key}={query[key]}" for key in sorted(query)))
    if body and method in {"POST", "PUT", "PATCH"}:
        parts.append(body)
    canonical = "\n".join(sorted(parts)).encode("utf-8")
    return base64.b64encode(
        hmac.new(signing_key, canonical, hashlib.sha256).digest()
    ).decode("ascii")


def common_header(version, serial, device_id, region="", logged_in=False, r1=False):
    # AppEnv.toHeader + GlassesEvenApiAuthenticator._buildCommon.
    fields = {
        "platform": "Android", "package": "com.even.sg",
        "versionName": "2.4.0", "build": "246", "brand": "Google",
        "model": "Pixel 8", "osVersion": "16", "carrier": "",
        "mcc": "", "mnc": "", "buildTime": "", "appId": 1001, "v": 3,
        "openUdid": device_id, "os": 1,
    }
    if serial:
        fields["ringSn" if r1 else "sn"] = serial
    if r1:
        fields["ringVer"] = version
    else:
        fields.update(verL=version, verR=version)
    fields["channel"] = "googlePlay"
    if logged_in:
        fields.update(sttLanguage="en-US", region=region)
    fields.update(
        sysLanguage="en-US", appLanguage="en-US",
        ts=datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        language="en", tzName="Asia/Bangkok", dateFmt="yyyy/MM/dd",
        timeFmt=24, unit="metrics",
    )
    return "&".join(f"{key}={quote_plus(str(value), safe='')}" for key, value in fields.items())


class EvenClient:
    def __init__(self, version=None, serial="", region="", timeout=30,
                 api_base=API_BASE, device_id=None, r1=False):
        try:
            parsed = urlsplit(api_base)
            _ = parsed.port  # Validate malformed/out-of-range ports before any request.
        except ValueError as exc:
            raise EvenError("API base must be a valid HTTPS origin.") from exc
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            raise EvenError("API base must be an HTTPS URL without credentials.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise EvenError("API base must contain only the HTTPS origin.")
        self.api_base = api_base.rstrip("/")
        self.r1 = r1
        self.version = version if version is not None else ("0.0.0" if r1 else "2.3.2.14")
        self.serial, self.region = serial, region
        self.timeout = timeout
        self.device_id = device_id or uuid.uuid4().hex
        self.token = ""
        self.opener = build_opener(NoRedirects())

    def request(self, method, path, query=None, payload=None):
        body = "" if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        common = common_header(self.version, self.serial, self.device_id, self.region, bool(self.token), self.r1)
        headers = {
            "common": common, "request-id": str(uuid.uuid4()),
            "user-agent": "Even/2.4.0 (com.even.sg; Android 16)",
            "accept": "application/json", "content-type": "application/json",
            "sign": signature(method, path, common, query, body, self.token),
        }
        if self.token:
            # Android 2.4.0 gates both headers on token presence, even for empty opRegion.
            headers.update(token=self.token, region=self.region)
        url = self.api_base + path
        if query:
            url += "?" + urlencode(query)
        request = Request(url, data=body.encode("utf-8") if payload is not None else None,
                          headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
        except HTTPError as exc:
            # Do not dump response bodies: login responses can contain credentials.
            raise EvenError(f"{path}: HTTP {exc.code}; check API domain and account status.", code=exc.code) from exc
        except (URLError, OSError, TimeoutError) as exc:
            raise EvenError(f"{path}: connection failed ({type(exc).__name__}).") from exc
        if len(raw) > 2_000_000:
            raise EvenError(f"{path}: response exceeds 2 MB.")
        try:
            envelope = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise EvenError(f"{path}: server returned invalid JSON.") from exc
        if not isinstance(envelope, dict) or type(envelope.get("code")) is not int:
            raise EvenError(f"{path}: unexpected response envelope.")
        if envelope["code"] != 0:
            message = str(envelope.get("msg", "Request rejected"))[:300]
            details = envelope.get("details")
            retry = details.get("retryAfterS") if isinstance(details, dict) else None
            suffix = f"; retry after {retry}s" if retry is not None else ""
            raise EvenError(f"{path}: API {envelope['code']}: {message}{suffix}", code=envelope["code"])
        return envelope.get("data")

    def login(self, email, password):
        data = self.request("POST", "/v2/g/login", payload={
            "email": email.strip(), "passwd": encode_password(password),
        })
        if not isinstance(data, dict) or not isinstance(data.get("token"), str) or not data["token"]:
            raise EvenError("Login succeeded but no token was returned.")
        self.token = data["token"]
        user = data.get("user")
        if not self.region and isinstance(user, dict) and isinstance(user.get("opRegion"), str):
            self.region = user["opRegion"]

    def check_firmware(self):
        return self.request("GET", "/v2/g/check_firmware", query={"is_ring": "true" if self.r1 else "false"})


def firmware_result(data, expected_version="2.4.0.24", device="G2"):
    if not isinstance(data, dict) or not data.get("subPath"):
        raise EvenError(f"No firmware offered. Supply your {device} serial with --serial and check account region.")
    version = data.get("version")
    if expected_version and version != expected_version:
        raise EvenError(f"Server offered {version!r}; expected {expected_version!r}. "
                        "Use --firmware-version VERSION to select the version you accept.")
    subpath = data["subPath"]
    if not isinstance(subpath, str):
        raise EvenError("Firmware subPath is not a string.")
    trusted_hosts = {urlsplit(base).hostname for base in CDN_BASES}
    try:
        urls = list(dict.fromkeys(urljoin(base + "/", subpath) for base in CDN_BASES))
        for url in urls:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.hostname not in trusted_hosts
                    or parsed.port not in (None, 443) or parsed.username is not None
                    or parsed.password is not None):
                raise ValueError("untrusted CDN origin")
    except ValueError as exc:
        raise EvenError("Firmware download URL must use a trusted Even HTTPS CDN.") from exc
    return {
        "version": version, "download_url": urls[0], "mirrors": urls[1:],
        "file_size": data.get("fileSize"), "file_sign": data.get("fileSign"),
        "sub_path": subpath,
    }


def firmware_version(value):
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", value):
        raise argparse.ArgumentTypeError("Use a three- or four-part firmware version, e.g. 0.0.0 or 2.3.2.14")
    return value


def check_with_login(client, email=None, save_login=False, no_saved_login=False):
    """Prefer a saved token; renew an expired saved session exactly once."""
    token = os.environ.get("EVEN_TOKEN", "")
    if token:
        if save_login:
            raise EvenError("Unset EVEN_TOKEN before --save-login so a password login can be saved.")
        client.token = token
        return client.check_firmware()
    store, saved = None, None
    requested_region = client.region
    if save_login or (not no_saved_login and CredentialStore.is_supported()):
        store = CredentialStore(client.api_base)
        saved = store.load()
    if email and saved and email.strip().casefold() != saved["email"].casefold():
        saved = None
    password = os.environ.get("EVEN_PASSWORD")
    if saved and not save_login:
        email = email or saved["email"]
        client.device_id = saved["device_id"]
        client.region = client.region or saved["region"]
        if saved["token"] and not password:
            client.token = saved["token"]
            try:
                return client.check_firmware()
            except EvenError as exc:
                if exc.code != 401:
                    raise
                client.token = ""
                saved = dict(saved, token="")
                store.save(saved)
        password = password or saved["password"]
    email = (email or (saved["email"] if saved else None) or input("Even email: ")).strip()
    password = password or getpass.getpass("Even password: ")
    if not email or not password:
        raise EvenError("Email and password are required.")
    if saved and not requested_region:
        client.region = ""  # Refresh the account's operating region from login.
    client.login(email, password)
    if store is not None and (save_login or saved):
        store.save({
            "schema": 1, "email": email, "password": password,
            "token": client.token, "region": client.region, "device_id": client.device_id,
        })
        if save_login:
            print("Login saved in macOS Keychain.", file=sys.stderr)
    return client.check_firmware()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=os.environ.get("EVEN_EMAIL"))
    parser.add_argument("--r1", action="store_true", help="Query R1 ring firmware instead of G2 glasses")
    parser.add_argument("--serial", help="Selected device serial (EVEN_GLASSES_SN or EVEN_RING_SN)")
    parser.add_argument("--current-version", type=firmware_version, help="Installed version; default G2: 2.3.2.14, R1: 0.0.0 (unknown)")
    parser.add_argument("--firmware-version", "--expected-version", dest="expected_version",
                        help="Require this offered version; default G2: 2.4.0.24, R1: any; empty string accepts any")
    parser.add_argument("--region", default=os.environ.get("EVEN_REGION", ""), help="Account opRegion; inferred after login")
    parser.add_argument("--api-base", default=API_BASE)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--json", action="store_true", help="Print firmware metadata as JSON")
    parser.add_argument("--dry-run", action="store_true", help="Show firmware request without credentials or network")
    login_options = parser.add_mutually_exclusive_group()
    login_options.add_argument("--save-login", action="store_true", help="Sign in and save/replace this API domain's login in macOS Keychain")
    login_options.add_argument("--forget-login", action="store_true", help="Remove this API domain's saved login and exit")
    login_options.add_argument("--no-saved-login", action="store_true", help="Skip saved login; do not read or write Keychain")
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise EvenError("Timeout must be positive.")
        device = "R1" if args.r1 else "G2"
        serial = args.serial
        if serial is None:
            serial = os.environ.get("EVEN_RING_SN" if args.r1 else "EVEN_GLASSES_SN", "")
        expected_version = args.expected_version
        if expected_version is None:
            expected_version = "" if args.r1 else "2.4.0.24"
        client = EvenClient(args.current_version, serial, args.region, args.timeout, args.api_base, r1=args.r1)
        if args.dry_run and (args.save_login or args.forget_login):
            raise EvenError("--dry-run cannot be combined with --save-login or --forget-login.")
        if args.forget_login:
            CredentialStore(client.api_base).forget()
            print("Saved login removed from macOS Keychain.", file=sys.stderr)
            return 0
        if args.dry_run:
            print(json.dumps({
                "method": "GET", "url": client.api_base + "/v2/g/check_firmware?is_ring=" + ("true" if args.r1 else "false"),
                "common": common_header(client.version, client.serial, client.device_id, r1=args.r1),
                "expected_version": expected_version,
            }, indent=2))
            return 0
        load_api_keys()  # Fail before prompting for credentials if app configuration is missing.
        data = check_with_login(client, args.email, args.save_login, args.no_saved_login)
        result = firmware_result(data, expected_version, device)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"{device} firmware: {result['version']} ({result['file_size']} bytes)", file=sys.stderr)
            print(result["download_url"])
        return 0
    except (EvenError, CredentialStoreError, ApiConfigError, CryptoError, EOFError, KeyboardInterrupt) as exc:
        print(f"Error: {exc or 'Cancelled'}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
