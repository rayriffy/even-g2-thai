"""Synthetic, public test keys; no extracted app constants."""

SIGNING_KEY = b"even-firmware-test-signing-key"
PASSWORD_KEY = b"0123456789abcdef0123456789abcdef"
API_ENV = {
    "EVEN_API_SIGNING_KEY": SIGNING_KEY.decode(),
    "EVEN_API_PASSWORD_KEY": PASSWORD_KEY.decode(),
}
