from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from even_api_config import ApiConfigError, load_api_keys
from even_api_fixture import API_ENV, PASSWORD_KEY, SIGNING_KEY
import even_firmware as even


class ApiConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "api.json"
        patcher = patch.dict(os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_environment_keys_do_not_require_a_config_file(self):
        with patch.dict(os.environ, API_ENV):
            self.assertEqual(load_api_keys(self.path), (SIGNING_KEY, PASSWORD_KEY))
        self.assertFalse(self.path.exists())

    def test_local_keys_are_ascii_text_not_hex_decoded(self):
        self.path.write_text(json.dumps({"signing_key": SIGNING_KEY.decode(),
                                         "password_key": PASSWORD_KEY.decode()}))
        self.assertEqual(load_api_keys(self.path), (SIGNING_KEY, PASSWORD_KEY))

    def test_environment_can_override_one_local_key(self):
        self.path.write_text(json.dumps({"signing_key": "local-fixture",
                                         "password_key": PASSWORD_KEY.decode()}))
        with patch.dict(os.environ, {"EVEN_API_SIGNING_KEY": SIGNING_KEY.decode()}):
            self.assertEqual(load_api_keys(self.path), (SIGNING_KEY, PASSWORD_KEY))

    def test_missing_keys_report_setup_without_values(self):
        with self.assertRaises(ApiConfigError) as error:
            load_api_keys(self.path)
        self.assertIn("EVEN_API_SIGNING_KEY", str(error.exception))

    def test_invalid_local_file_is_rejected(self):
        for value in ("invalid-json", "[]", '{"signing_key":"fixture"}'):
            with self.subTest(value=value):
                self.path.write_text(value)
                with self.assertRaises(ApiConfigError):
                    load_api_keys(self.path)

    def test_invalid_keys_are_rejected_without_echoing_them(self):
        for password in ("invalid-private-value", "ก" * 32):
            with self.subTest(password=password):
                env = dict(API_ENV, EVEN_API_PASSWORD_KEY=password)
                with patch.dict(os.environ, env), self.assertRaises(ApiConfigError) as error:
                    load_api_keys(self.path)
                self.assertNotIn(password, str(error.exception))

    def test_cli_missing_configuration_fails_before_password_prompt(self):
        with patch("even_firmware.load_api_keys", side_effect=ApiConfigError("Configure app keys")):
            with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
                with redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(even.main([]), 1)
        self.assertIn("Configure app keys", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
