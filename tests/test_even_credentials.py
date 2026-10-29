from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from even_credentials import CredentialStore, CredentialStoreError
import even_firmware as even
from even_api_fixture import API_ENV


RECORD = {
    "schema": 1, "email": "fixture@example.com", "password": "fixture-password",
    "token": "fixture-saved-token", "region": "US", "device_id": "fixture-device",
}
FIRMWARE = {"version": "2.4.0.24", "subPath": "/firmware/fixture.bin"}


class SavedLoginTests(unittest.TestCase):
    def setUp(self):
        env_patch = patch.dict(os.environ, API_ENV, clear=True)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        store_patch = patch("even_firmware.CredentialStore")
        self.store_class = store_patch.start()
        self.addCleanup(store_patch.stop)
        self.store_class.is_supported.return_value = True
        self.store = self.store_class.return_value
        self.store.load.return_value = dict(RECORD)
        self.client = Mock(api_base=even.API_BASE, token="", region="", device_id="new-device")
        self.client.check_firmware.return_value = FIRMWARE
        self.client.login.side_effect = self.login_success
        input_patch = patch("builtins.input", side_effect=AssertionError("unexpected email prompt"))
        input_patch.start()
        self.addCleanup(input_patch.stop)
        password_patch = patch("even_firmware.getpass.getpass", side_effect=AssertionError("unexpected password prompt"))
        self.password_prompt = password_patch.start()
        self.addCleanup(password_patch.stop)

    def login_success(self, email, password):
        self.client.token = "fixture-renewed-token"
        self.client.region = "US"

    def test_cached_session_skips_password_and_login(self):
        self.assertEqual(even.check_with_login(self.client), FIRMWARE)
        self.client.login.assert_not_called()
        self.client.check_firmware.assert_called_once()
        self.assertEqual(self.client.token, RECORD["token"])
        self.assertEqual(self.client.device_id, RECORD["device_id"])
        self.assertEqual(self.client.region, RECORD["region"])
        self.store.save.assert_not_called()
        self.store_class.assert_called_once_with(even.API_BASE)

    def test_fake_backend_support_is_independent_of_callers_platform(self):
        with patch("even_firmware.sys", SimpleNamespace(platform="linux", stderr=sys.stderr)):
            self.assertEqual(even.check_with_login(self.client), FIRMWARE)
        self.client.login.assert_not_called()
        self.store.load.assert_called_once()

    def test_unsupported_backend_skips_saved_login(self):
        self.store_class.is_supported.return_value = False
        with patch.dict(os.environ, {"EVEN_PASSWORD": "fixture-override"}):
            even.check_with_login(self.client, email=RECORD["email"])
        self.store_class.assert_not_called()
        self.client.login.assert_called_once_with(RECORD["email"], "fixture-override")

    def test_real_store_rejects_unsupported_platform_before_loading_native_apis(self):
        with patch("even_credentials.sys", SimpleNamespace(platform="linux")):
            self.assertFalse(CredentialStore.is_supported())
            with patch("even_credentials.ct.CDLL", side_effect=AssertionError("unexpected native API")):
                with self.assertRaises(CredentialStoreError):
                    CredentialStore(even.API_BASE).load()

    def test_save_login_prompts_and_replaces_record_after_success(self):
        self.password_prompt.side_effect = None
        self.password_prompt.return_value = "fixture-new-password"
        with redirect_stderr(io.StringIO()):
            even.check_with_login(self.client, save_login=True)
        self.client.login.assert_called_once_with(RECORD["email"], "fixture-new-password")
        saved = self.store.save.call_args.args[0]
        self.assertEqual(saved["password"], "fixture-new-password")
        self.assertEqual(saved["token"], "fixture-renewed-token")

    def test_expired_session_renews_once_and_replaces_token(self):
        self.client.check_firmware.side_effect = [even.EvenError("Expired", code=401), FIRMWARE]
        self.assertEqual(even.check_with_login(self.client), FIRMWARE)
        self.client.login.assert_called_once_with(RECORD["email"], RECORD["password"])
        self.assertEqual(self.client.check_firmware.call_count, 2)
        saved = [call.args[0] for call in self.store.save.call_args_list]
        self.assertEqual([r["token"] for r in saved], ["", "fixture-renewed-token"])

    def test_second_401_does_not_loop(self):
        self.client.check_firmware.side_effect = even.EvenError("Expired", code=401)
        with self.assertRaises(even.EvenError):
            even.check_with_login(self.client)
        self.client.login.assert_called_once()
        self.assertEqual(self.client.check_firmware.call_count, 2)

    def test_refresh_reloads_account_region(self):
        self.client.check_firmware.side_effect = [even.EvenError("Expired", code=401), FIRMWARE]

        def moved_region(email, password):
            self.assertEqual(self.client.region, "")
            self.client.token = "fixture-renewed-token"
            self.client.region = "EU"

        self.client.login.side_effect = moved_region
        even.check_with_login(self.client)
        self.assertEqual(self.store.save.call_args.args[0]["region"], "EU")

    def test_network_error_does_not_reauthenticate(self):
        self.client.check_firmware.side_effect = even.EvenError("Connection failed")
        with self.assertRaises(even.EvenError):
            even.check_with_login(self.client)
        self.client.login.assert_not_called()
        self.store.save.assert_not_called()

    def test_failed_login_does_not_save_or_check_firmware(self):
        self.client.login.side_effect = even.EvenError("Account locked", code=1119)
        with patch.dict(os.environ, {"EVEN_PASSWORD": "fixture-override"}):
            with self.assertRaises(even.EvenError):
                even.check_with_login(self.client, save_login=True)
        self.store.save.assert_not_called()
        self.client.check_firmware.assert_not_called()

    def test_other_account_does_not_reuse_or_replace_saved_login(self):
        with patch.dict(os.environ, {"EVEN_PASSWORD": "other-password"}):
            even.check_with_login(self.client, email="other@example.com")
        self.client.login.assert_called_once_with("other@example.com", "other-password")
        self.store.save.assert_not_called()
        self.assertEqual(self.client.device_id, "new-device")

    def test_no_saved_login_bypasses_keychain(self):
        with patch.dict(os.environ, {"EVEN_PASSWORD": "fixture-override"}):
            even.check_with_login(self.client, email=RECORD["email"], no_saved_login=True)
        self.store_class.assert_not_called()
        self.client.login.assert_called_once_with(RECORD["email"], "fixture-override")

    def test_environment_token_bypasses_keychain_and_refresh(self):
        with patch.dict(os.environ, {"EVEN_TOKEN": "environment-token"}):
            even.check_with_login(self.client)
        self.store_class.assert_not_called()
        self.client.login.assert_not_called()
        self.assertEqual(self.client.token, "environment-token")

    def test_environment_token_cannot_be_saved_as_password_login(self):
        with patch.dict(os.environ, {"EVEN_TOKEN": "environment-token"}):
            with self.assertRaises(even.EvenError):
                even.check_with_login(self.client, save_login=True)
        self.store_class.assert_not_called()

    def test_explicit_password_overrides_saved_token_and_password(self):
        with patch.dict(os.environ, {"EVEN_PASSWORD": "fixture-override"}):
            even.check_with_login(self.client)
        self.client.login.assert_called_once_with(RECORD["email"], "fixture-override")
        self.assertEqual(self.store.save.call_args.args[0]["password"], "fixture-override")

    def test_keychain_failure_is_actionable_without_secret_output(self):
        self.store.load.side_effect = CredentialStoreError("Keychain locked; use --no-saved-login")
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(even.main([]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("--no-saved-login", errors.getvalue())
        for secret in (RECORD["token"], RECORD["password"]):
            self.assertNotIn(secret, errors.getvalue())

    def test_forget_removes_only_selected_domain_without_network(self):
        with patch("even_firmware.EvenClient.check_firmware") as check:
            with redirect_stderr(io.StringIO()):
                self.assertEqual(even.main(["--forget-login", "--api-base", "https://other.example.com"]), 0)
        self.store_class.assert_called_once_with("https://other.example.com")
        self.store.forget.assert_called_once()
        self.store.load.assert_not_called()
        check.assert_not_called()

    def test_dry_run_does_not_access_keychain(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(even.main(["--dry-run"]), 0)
        self.store_class.assert_not_called()

    def test_dry_run_rejects_keychain_mutations(self):
        for flag in ("--save-login", "--forget-login"):
            with self.subTest(flag=flag), redirect_stderr(io.StringIO()):
                self.assertEqual(even.main(["--dry-run", flag]), 1)
        self.store_class.assert_not_called()

    def test_store_identity_is_domain_scoped(self):
        a = CredentialStore("https://api.evenrealities.com")
        b = CredentialStore("https://other.example.com")
        self.assertNotEqual(a.service, b.service)

    def test_invalid_record_is_rejected_without_secret_echo(self):
        with self.assertRaises(CredentialStoreError) as context:
            CredentialStore._validate(dict(RECORD, schema=999))
        self.assertNotIn(RECORD["password"], str(context.exception))


@unittest.skipUnless(sys.platform == "darwin" and os.environ.get("EVEN_TEST_KEYCHAIN") == "1",
                     "Set EVEN_TEST_KEYCHAIN=1 to test a temporary native Keychain item")
class NativeKeychainTests(unittest.TestCase):
    def test_real_keychain_add_read_update_delete(self):
        store = CredentialStore("https://" + uuid.uuid4().hex + ".keychain-test.invalid")
        try:
            self.assertIsNone(store.load())
            store.save(dict(RECORD))
            self.assertEqual(store.load(), RECORD)
            updated = dict(RECORD, password="fixture-updated-รหัสผ่าน", token="fixture-updated-token")
            store.save(updated)
            self.assertEqual(store.load(), updated)
        finally:
            store.forget()
        self.assertIsNone(store.load())
        store.forget()


if __name__ == "__main__":
    unittest.main()
