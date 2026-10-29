import base64
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import even_firmware as even
from even_api_fixture import API_ENV, SIGNING_KEY


FIRMWARE = {
    "version": "2.4.0.24", "subPath": "/firmware/fixture.bin",
    "fileSize": 123456, "fileSign": "fixture-file-sign",
}


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, API_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_password_vectors_verified_with_apple_commoncrypto(self):
        vectors = {
            "test-password": "SZ3tFxk+ZcWWcDjqQ7OznQ==",
            "รหัสผ่าน🔐": "/lOJozRiP8NfjXPBGAbkLgV3EhJnOtAszMg4Oofddg4=",
            "0123456789abcdef": "rJqScgGtNiuSxAM0aBAD+9na2QRsl9qQvedYafqXf2I=",
        }
        for password, expected in vectors.items():
            with self.subTest(password=password):
                self.assertEqual(even.encode_password(password), expected)

    def test_signature_vector(self):
        self.assertEqual(even.signature(
            "GET", "/v2/g/check_firmware",
            "platform=Android&verL=2.3.2.14&verR=2.3.2.14",
            query={"is_ring": "false"}, token="fixture-token",
        ), "FdKRXnFn4gWBfzpiKZXAz5/TwGlppxWkAd8cd3butCQ=")

    def test_signature_sorts_query_keys_without_url_encoding_values(self):
        query = {"z": "a b", "a": "a/b"}
        canonical = "/path\nGET\na=a/b&z=a b\ncommon"
        expected = base64.b64encode(hmac.new(
            SIGNING_KEY, canonical.encode(), hashlib.sha256,
        ).digest()).decode()
        self.assertEqual(even.signature("GET", "/path", "common", query), expected)

    def test_post_signs_exact_body_but_get_does_not(self):
        body = '{"email":"fixture@example.com","passwd":"ciphertext"}'
        self.assertNotEqual(even.signature("POST", "/path", "common", body=body),
                            even.signature("POST", "/path", "common"))
        self.assertEqual(even.signature("GET", "/path", "common", body=body),
                         even.signature("GET", "/path", "common"))

    def test_common_header_encodes_values_and_both_leg_versions(self):
        fields = parse_qs(even.common_header("2.3.2.14", "G2 +&/", "fixture-id"))
        self.assertEqual(fields["sn"], ["G2 +&/"])
        self.assertEqual(fields["verL"], ["2.3.2.14"])
        self.assertEqual(fields["verR"], ["2.3.2.14"])
        self.assertEqual(fields["os"], ["1"])
        self.assertEqual(fields["appId"], ["1001"])
        self.assertEqual(fields["v"], ["3"])
        self.assertTrue(fields["ts"][0].endswith("Z"))

    def test_firmware_url_and_mirrors(self):
        result = even.firmware_result(FIRMWARE)
        self.assertEqual(result["download_url"],
                         "https://cdn-az.evenrealities.com/firmware/fixture.bin")
        self.assertEqual(len(result["mirrors"]), 2)
        self.assertEqual(result["file_sign"], "fixture-file-sign")

    def test_absolute_https_download_url_preserved(self):
        result = even.firmware_result(dict(FIRMWARE, subPath="https://cdn.evenreal.co/fw.bin?q=1"))
        self.assertEqual(result["download_url"], "https://cdn.evenreal.co/fw.bin?q=1")
        self.assertEqual(result["mirrors"], [])

    def test_missing_firmware_and_wrong_version_fail(self):
        for data in [None, {}, dict(FIRMWARE, version="2.3.2.14")]:
            with self.subTest(data=data), self.assertRaises(even.EvenError):
                even.firmware_result(data)

    def test_insecure_download_url_rejected(self):
        with self.assertRaises(even.EvenError):
            even.firmware_result(dict(FIRMWARE, subPath="http://example.com/fw.bin"))

    def test_firmware_authority_overrides_are_rejected(self):
        for subpath in ("https://evil.example/fw.bin", "//evil.example/fw.bin",
                        "https://user@cdn.evenreal.co/fw.bin", "https://@cdn.evenreal.co/fw.bin",
                        "https://cdn.evenreal.co:8443/fw.bin", "https://[invalid/fw.bin"):
            with self.subTest(subpath=subpath), self.assertRaises(even.EvenError):
                even.firmware_result(dict(FIRMWARE, subPath=subpath))

    def test_password_encryption_never_launches_a_child_process(self):
        with patch("subprocess.Popen", side_effect=AssertionError("unexpected child process")):
            self.assertEqual(even.encode_password("test-password"), "SZ3tFxk+ZcWWcDjqQ7OznQ==")

    def test_insecure_or_malformed_api_base_rejected(self):
        for base in ["http://example.com", "https://user:pass@example.com", "https://example.com/path"]:
            with self.subTest(base=base), self.assertRaises(even.EvenError):
                even.EvenClient(api_base=base)

    def test_malformed_api_authority_reports_a_clean_cli_error(self):
        for base in ("https://[invalid", "https://example.com:invalid",
                     "https://example.com:70000", "https://:443", "https://@example.com"):
            with self.subTest(base=base):
                errors = io.StringIO()
                with redirect_stderr(errors):
                    self.assertEqual(even.main(["--api-base", base, "--dry-run"]), 1)
                self.assertIn("Error:", errors.getvalue())
                self.assertNotIn("Traceback", errors.getvalue())

    def test_empty_region_follows_android_240_token_contract(self):
        client = even.EvenClient()
        client.token = "fixture-token"
        with patch.object(client.opener, "open") as opener:
            opener.return_value.__enter__.return_value.read.return_value = b'{"code":0,"data":null}'
            client.check_firmware()
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Region"), "")
        fields = parse_qs(request.get_header("Common"), keep_blank_values=True)
        self.assertEqual(fields["region"], [""])

    def test_dry_run_needs_no_credentials_or_network(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
                self.assertEqual(even.main(["--dry-run"]), 0)
        data = json.loads(output.getvalue())
        self.assertIn("is_ring=false", data["url"])
        self.assertIn("verL=2.3.2.14&verR=2.3.2.14", data["common"])

    def test_r1_header_uses_ring_fields(self):
        fields = parse_qs(even.common_header("1.2.3.4", "R1 +&/", "fixture-id", r1=True))
        self.assertEqual(fields["ringSn"], ["R1 +&/"])
        self.assertEqual(fields["ringVer"], ["1.2.3.4"])
        for key in ("sn", "verL", "verR"):
            self.assertNotIn(key, fields)

    def test_r1_dry_run_uses_ring_environment_and_defaults(self):
        output = io.StringIO()
        env = {"EVEN_RING_SN": "fixture-r1", "EVEN_GLASSES_SN": "fixture-g2"}
        with patch.dict(os.environ, env, clear=True), redirect_stdout(output):
            self.assertEqual(even.main(["--r1", "--dry-run"]), 0)
        data = json.loads(output.getvalue())
        self.assertIn("is_ring=true", data["url"])
        self.assertEqual(data["expected_version"], "")
        fields = parse_qs(data["common"])
        self.assertEqual(fields["ringSn"], ["fixture-r1"])
        self.assertEqual(fields["ringVer"], ["0.0.0"])
        self.assertNotIn("sn", fields)

    def test_r1_does_not_reuse_glasses_serial(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"EVEN_GLASSES_SN": "fixture-g2"}, clear=True):
            with redirect_stdout(output):
                self.assertEqual(even.main(["--r1", "--dry-run"]), 0)
        self.assertNotIn("fixture-g2", output.getvalue())

    def test_firmware_version_override_in_dry_run(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(even.main(["--dry-run", "--firmware-version", "3.0.0.1"]), 0)
        self.assertEqual(json.loads(output.getvalue())["expected_version"], "3.0.0.1")


class LoopbackFlowTests(unittest.TestCase):
    """Run CLI login -> signed check -> URL output against an HTTP fixture."""

    @classmethod
    def setUpClass(cls):
        cls.errors, cls.requests = [], []
        cls.check_response = {"code": 0, "msg": "OK", "data": FIRMWARE}
        cls.login_response = None

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.handle_api()

            def do_GET(self):
                self.handle_api()

            def handle_api(self):
                try:
                    body = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode()
                    uri = urlsplit(self.path)
                    query = parse_qs(uri.query)
                    common = self.headers["common"]
                    fields = parse_qs(common)
                    if cls.r1:
                        assert fields["ringVer"] == [cls.current_version]
                        assert fields["ringSn"] == ["fixture-r1"]
                        assert not any(key in fields for key in ("sn", "verL", "verR"))
                    else:
                        assert fields["verL"] == fields["verR"] == [cls.current_version]
                        assert "ringVer" not in fields and "ringSn" not in fields
                    parts = [self.command, uri.path, common]
                    if self.headers.get("token"):
                        parts.append(self.headers["token"])
                    if query:
                        parts.append("&".join(f"{k}={query[k][0]}" for k in sorted(query)))
                    if body:
                        parts.append(body)
                    expected = base64.b64encode(hmac.new(
                        SIGNING_KEY, "\n".join(sorted(parts)).encode(), hashlib.sha256,
                    ).digest()).decode()
                    assert self.headers["sign"] == expected
                    cls.requests.append((self.command, uri.path, self.headers["request-id"]))
                    if uri.path == "/v2/g/login":
                        assert self.command == "POST"
                        assert json.loads(body) == {
                            "email": "fixture@example.com", "passwd": "SZ3tFxk+ZcWWcDjqQ7OznQ==",
                        }
                        assert not self.headers.get("token")
                        response = cls.login_response or {"code": 0, "msg": "OK", "data": {
                            "token": "fixture-token", "user": {"opRegion": "US"},
                        }}
                    else:
                        assert self.command == "GET" and uri.path == "/v2/g/check_firmware"
                        assert query == {"is_ring": ["true" if cls.r1 else "false"]}
                        assert self.headers["token"] == "fixture-token"
                        assert self.headers["region"] == "US"
                        assert fields["region"] == ["US"]
                        response = cls.check_response.pop(0) if isinstance(cls.check_response, list) else cls.check_response
                except Exception as exc:
                    cls.errors.append(repr(exc))
                    response = {"code": 900, "msg": "Fixture assertion failed"}
                encoded = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def run_cli(self, response, login_response=None, extra_args=(), current_version=None,
                saved_login=None, password_env=True):
        self.__class__.errors.clear()
        self.__class__.requests.clear()
        self.__class__.check_response = response
        self.__class__.login_response = login_response
        self.__class__.r1 = "--r1" in extra_args
        self.__class__.current_version = current_version or ("0.0.0" if self.r1 else "2.3.2.14")
        original_open = build_opener(even.NoRedirects()).open
        origin = f"http://127.0.0.1:{self.server.server_port}"

        def local_open(opener, request, timeout):
            url = urlsplit(request.full_url)
            local = Request(origin + url.path + ("?" + url.query if url.query else ""),
                            data=request.data, headers=dict(request.header_items()), method=request.method)
            return original_open(local, timeout=timeout)

        output, errors = io.StringIO(), io.StringIO()
        env = dict(API_ENV)
        if password_env:
            env["EVEN_PASSWORD"] = "test-password"
        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.OpenerDirector.open", local_open), patch("even_firmware.CredentialStore") as store:
                self.last_store = store.return_value
                self.last_store.load.return_value = saved_login
                with redirect_stdout(output), redirect_stderr(errors):
                    code = even.main([
                        "--email", "fixture@example.com", "--serial",
                        "fixture-r1" if self.r1 else "fixture-g2", "--json", *extra_args,
                    ])
        self.assertEqual(self.errors, [])
        self.assertNotIn("fixture-token", output.getvalue() + errors.getvalue())
        self.assertNotIn("test-password", output.getvalue() + errors.getvalue())
        return code, output.getvalue(), errors.getvalue()

    def test_cli_login_check_and_url_resolution(self):
        code, output, _ = self.run_cli({"code": 0, "msg": "OK", "data": FIRMWARE})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["version"], "2.4.0.24")
        self.assertEqual([r[:2] for r in self.requests],
                         [("POST", "/v2/g/login"), ("GET", "/v2/g/check_firmware")])
        self.assertNotEqual(self.requests[0][2], self.requests[1][2])

    def test_cli_saves_successful_login_in_keychain(self):
        code, _, _ = self.run_cli(
            {"code": 0, "msg": "OK", "data": FIRMWARE}, extra_args=("--save-login",),
        )
        self.assertEqual(code, 0)
        saved = self.last_store.save.call_args.args[0]
        self.assertEqual(saved["email"], "fixture@example.com")
        self.assertEqual(saved["password"], "test-password")
        self.assertEqual(saved["token"], "fixture-token")
        self.assertEqual(saved["region"], "US")

    def test_cli_reuses_saved_token_for_g2_and_r1(self):
        saved = {"schema": 1, "email": "fixture@example.com", "password": "test-password",
                 "token": "fixture-token", "region": "US", "device_id": "fixture-device"}
        for args in ((), ("--r1",)):
            with self.subTest(args=args):
                code, _, _ = self.run_cli(
                    {"code": 0, "msg": "OK", "data": FIRMWARE}, extra_args=args,
                    saved_login=saved, password_env=False,
                )
                self.assertEqual(code, 0)
                self.assertEqual([r[:2] for r in self.requests], [("GET", "/v2/g/check_firmware")])

    def test_cli_renews_saved_session_once(self):
        saved = {"schema": 1, "email": "fixture@example.com", "password": "test-password",
                 "token": "fixture-token", "region": "US", "device_id": "fixture-device"}
        code, _, _ = self.run_cli(
            [{"code": 401, "msg": "Session expired"}, {"code": 0, "msg": "OK", "data": FIRMWARE}],
            saved_login=saved, password_env=False,
        )
        self.assertEqual(code, 0)
        self.assertEqual([r[:2] for r in self.requests],
                         [("GET", "/v2/g/check_firmware"), ("POST", "/v2/g/login"),
                          ("GET", "/v2/g/check_firmware")])

    def test_expired_session_exits_without_url(self):
        code, output, errors = self.run_cli({"code": 401, "msg": "Session expired"})
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("API 401", errors)

    def test_locked_account_stops_after_one_login(self):
        code, output, errors = self.run_cli(None, login_response={
            "code": 1119, "msg": "Account locked", "details": {"retryAfterS": 60},
        })
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("retry after 60s", errors)
        self.assertEqual(len(self.requests), 1)

    def test_login_without_token_stops_before_firmware_check(self):
        code, output, errors = self.run_cli(None, login_response={"code": 0, "msg": "OK", "data": {}})
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("no token", errors)
        self.assertEqual(len(self.requests), 1)

    def test_wrong_firmware_version_exits_without_url(self):
        code, output, errors = self.run_cli({"code": 0, "msg": "OK", "data": dict(FIRMWARE, version="2.4.0.25")})
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("expected '2.4.0.24'", errors)

    def test_custom_target_and_legacy_alias(self):
        for option in ("--firmware-version", "--expected-version"):
            with self.subTest(option=option):
                data = dict(FIRMWARE, version="3.0.0.1")
                code, output, _ = self.run_cli(
                    {"code": 0, "msg": "OK", "data": data}, extra_args=(option, "3.0.0.1"),
                )
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(output)["version"], "3.0.0.1")

    def test_r1_login_signed_check_and_custom_target(self):
        data = dict(FIRMWARE, version="1.2.3.4", subPath="/firmware/ring.bin")
        code, output, _ = self.run_cli(
            {"code": 0, "msg": "OK", "data": data}, current_version="1.0.0.0",
            extra_args=("--r1", "--current-version", "1.0.0.0", "--firmware-version", "1.2.3.4"),
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["download_url"],
                         "https://cdn-az.evenrealities.com/firmware/ring.bin")
        self.assertEqual(len(self.requests), 2)

    def test_r1_default_accepts_server_version(self):
        code, output, _ = self.run_cli(
            {"code": 0, "msg": "OK", "data": dict(FIRMWARE, version="1.2.3")},
            extra_args=("--r1",),
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["version"], "1.2.3")

    def test_r1_mismatch_and_missing_firmware(self):
        cases = [(dict(FIRMWARE, version="1.2.4.0"), "expected '1.2.3.4'"),
                 (None, "your R1 serial")]
        for data, expected in cases:
            with self.subTest(data=data):
                code, output, errors = self.run_cli(
                    {"code": 0, "msg": "OK", "data": data},
                    extra_args=("--r1", "--firmware-version", "1.2.3.4"),
                )
                self.assertEqual(code, 1)
                self.assertEqual(output, "")
                self.assertIn(expected, errors)


if __name__ == "__main__":
    unittest.main()
