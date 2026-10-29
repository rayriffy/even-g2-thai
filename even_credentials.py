"""macOS Keychain storage through Security.framework; no secret subprocess args."""

from contextlib import contextmanager
import ctypes as ct
import json
import sys


class CredentialStoreError(Exception):
    pass


class CredentialStore:
    """One saved login per API origin, shared by G2 and R1."""

    @staticmethod
    def is_supported():
        return sys.platform == "darwin"

    def __init__(self, api_base):
        self.service = "com.rayriffy.even-firmware:" + api_base
        self._cf = None
        self._security = None

    def _connect(self):
        if self._cf is not None:
            return
        if not self.is_supported():
            raise CredentialStoreError("Saved login requires macOS Keychain.")
        try:
            self._cf = ct.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            self._security = ct.CDLL("/System/Library/Frameworks/Security.framework/Security")
            definitions = {
                "CFDictionaryCreateMutable": ([ct.c_void_p, ct.c_long, ct.c_void_p, ct.c_void_p], ct.c_void_p),
                "CFDictionarySetValue": ([ct.c_void_p, ct.c_void_p, ct.c_void_p], None),
                "CFStringCreateWithCString": ([ct.c_void_p, ct.c_char_p, ct.c_uint32], ct.c_void_p),
                "CFDataCreate": ([ct.c_void_p, ct.c_char_p, ct.c_long], ct.c_void_p),
                "CFDataGetBytePtr": ([ct.c_void_p], ct.c_void_p),
                "CFDataGetLength": ([ct.c_void_p], ct.c_long),
                "CFRelease": ([ct.c_void_p], None),
            }
            for name, (args, result) in definitions.items():
                function = getattr(self._cf, name)
                function.argtypes, function.restype = args, result
            for name, args in {
                "SecItemCopyMatching": [ct.c_void_p, ct.POINTER(ct.c_void_p)],
                "SecItemAdd": [ct.c_void_p, ct.c_void_p],
                "SecItemUpdate": [ct.c_void_p, ct.c_void_p],
                "SecItemDelete": [ct.c_void_p],
            }.items():
                function = getattr(self._security, name)
                function.argtypes, function.restype = args, ct.c_int32
        except (OSError, AttributeError) as exc:
            self._cf = self._security = None
            raise CredentialStoreError("Cannot load macOS Keychain APIs.") from exc

    def _constant(self, name):
        return ct.c_void_p.in_dll(self._security, name)

    @contextmanager
    def _dictionary(self, fields):
        self._connect()
        key_callbacks = ct.addressof(ct.c_byte.in_dll(self._cf, "kCFTypeDictionaryKeyCallBacks"))
        value_callbacks = ct.addressof(ct.c_byte.in_dll(self._cf, "kCFTypeDictionaryValueCallBacks"))
        reference = self._cf.CFDictionaryCreateMutable(None, 0, key_callbacks, value_callbacks)
        if not reference:
            raise CredentialStoreError("Cannot allocate Keychain query.")
        try:
            for key, value in fields.items():
                owned = not isinstance(value, (ct.c_void_p, bool))
                if isinstance(value, bool):
                    symbol = "kCFBooleanTrue" if value else "kCFBooleanFalse"
                    item = ct.c_void_p.in_dll(self._cf, symbol)
                elif isinstance(value, ct.c_void_p):
                    item = value
                elif isinstance(value, bytes):
                    item = self._cf.CFDataCreate(None, value, len(value))
                else:
                    item = self._cf.CFStringCreateWithCString(None, value.encode("utf-8"), 0x08000100)
                if not item:
                    raise CredentialStoreError("Cannot allocate Keychain value.")
                try:
                    self._cf.CFDictionarySetValue(reference, self._constant(key), item)
                finally:
                    if owned:
                        self._cf.CFRelease(item)
            yield reference
        finally:
            self._cf.CFRelease(reference)

    def _query(self):
        self._connect()
        return {
            "kSecClass": self._constant("kSecClassGenericPassword"),
            "kSecAttrService": self.service, "kSecAttrAccount": "saved-login",
        }

    @staticmethod
    def _check(status):
        if status:
            raise CredentialStoreError(
                f"Keychain operation failed (OSStatus {status}). "
                "Unlock your login keychain, or use --no-saved-login."
            )

    @staticmethod
    def _validate(record):
        keys = ("email", "password", "token", "region", "device_id")
        if (not isinstance(record, dict) or record.get("schema") != 1
                or any(not isinstance(record.get(key), str) for key in keys)
                or not record["email"] or not record["password"] or not record["device_id"]):
            raise CredentialStoreError("Saved login is invalid; use --forget-login and save it again.")
        return record

    def load(self):
        query = self._query()
        query.update(kSecReturnData=True, kSecMatchLimit=self._constant("kSecMatchLimitOne"))
        result = ct.c_void_p()
        with self._dictionary(query) as reference:
            status = self._security.SecItemCopyMatching(reference, ct.byref(result))
        if status == -25300:  # errSecItemNotFound
            return None
        self._check(status)
        if not result.value:
            raise CredentialStoreError("Keychain returned an empty saved login.")
        try:
            size = self._cf.CFDataGetLength(result)
            if not 0 < size <= 65536:
                raise CredentialStoreError("Saved login has an invalid size.")
            raw = ct.string_at(self._cf.CFDataGetBytePtr(result), size)
        finally:
            self._cf.CFRelease(result)
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise CredentialStoreError("Saved login is invalid; use --forget-login.") from exc
        return self._validate(record)

    def save(self, record):
        data = json.dumps(self._validate(record), ensure_ascii=False).encode("utf-8")
        with self._dictionary(self._query()) as query:
            with self._dictionary({"kSecValueData": data}) as values:
                status = self._security.SecItemUpdate(query, values)
        if status == -25300:
            fields = self._query()
            fields.update(kSecValueData=data, kSecAttrLabel="Even firmware saved login")
            with self._dictionary(fields) as attributes:
                status = self._security.SecItemAdd(attributes, None)
        self._check(status)

    def forget(self):
        with self._dictionary(self._query()) as query:
            status = self._security.SecItemDelete(query)
        if status != -25300:
            self._check(status)
