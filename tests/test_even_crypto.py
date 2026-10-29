import base64
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from even_crypto import CryptoError, _openssl, encrypt_aes_cbc
from even_api_fixture import PASSWORD_KEY


class NativeCryptoTests(unittest.TestCase):
    def test_invalid_key_or_iv_is_rejected(self):
        for key, iv in ((b"short", bytes(range(1, 17))), (PASSWORD_KEY, b"short")):
            with self.subTest(key=key, iv=iv), self.assertRaises(CryptoError):
                encrypt_aes_cbc(b"test", key, iv)

    def test_libcrypto_matches_independent_commoncrypto_vectors(self):
        library = None
        if sys.platform == "darwin":
            candidates = [Path('/opt/homebrew/opt/openssl@3/lib/libcrypto.dylib'),
                          Path('/usr/local/opt/openssl@3/lib/libcrypto.dylib')]
            library = next((str(p) for p in candidates if p.exists()), None)
            if library is None:
                self.skipTest("OpenSSL library not installed on this Mac")
        vectors = {
            "test-password": "SZ3tFxk+ZcWWcDjqQ7OznQ==",
            "รหัสผ่าน🔐": "/lOJozRiP8NfjXPBGAbkLgV3EhJnOtAszMg4Oofddg4=",
            "0123456789abcdef": "rJqScgGtNiuSxAM0aBAD+9na2QRsl9qQvedYafqXf2I=",
        }
        for text, expected in vectors.items():
            with self.subTest(text=text):
                encrypted = _openssl(text.encode(), PASSWORD_KEY, bytes(range(1, 17)), library)
                self.assertEqual(base64.b64encode(encrypted).decode(), expected)


if __name__ == "__main__":
    unittest.main()
