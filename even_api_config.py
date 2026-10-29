"""Load extracted app constants from private local configuration or the environment."""

import json
import os
from pathlib import Path


class ApiConfigError(Exception):
    pass


def load_api_keys(config_path=None):
    """Use ASCII key text verbatim, never hex-decode the app constants."""
    signing = os.environ.get("EVEN_API_SIGNING_KEY")
    password = os.environ.get("EVEN_API_PASSWORD_KEY")
    if signing is None or password is None:
        path = Path(config_path) if config_path is not None else Path(__file__).resolve().parent / ".cache/even-api.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        except (OSError, ValueError, UnicodeError) as exc:
            raise ApiConfigError("Cannot read local API configuration; see docs/firmware-download.md.") from exc
        if not isinstance(data, dict):
            raise ApiConfigError("Local API configuration must be a JSON object.")
        signing = signing if signing is not None else data.get("signing_key")
        password = password if password is not None else data.get("password_key")
    if not isinstance(signing, str) or not signing or not isinstance(password, str) or not password:
        raise ApiConfigError(
            "Configure the extracted app keys in .cache/even-api.json or set "
            "EVEN_API_SIGNING_KEY and EVEN_API_PASSWORD_KEY; see docs/firmware-download.md."
        )
    try:
        signing_bytes, password_bytes = signing.encode("ascii"), password.encode("ascii")
    except UnicodeError as exc:
        raise ApiConfigError("App API keys must contain ASCII text.") from exc
    if len(password_bytes) != 32:
        raise ApiConfigError("The app password key must contain exactly 32 ASCII bytes.")
    return signing_bytes, password_bytes
