"""In-process AES-256-CBC/PKCS7 through operating-system crypto libraries."""

import ctypes as ct
import sys


class CryptoError(Exception):
    pass


def _commoncrypto(data, key, iv):
    library = ct.CDLL("/usr/lib/system/libcommonCrypto.dylib")
    encrypt = library.CCCrypt
    encrypt.argtypes = [ct.c_uint, ct.c_uint, ct.c_uint, ct.c_char_p, ct.c_size_t,
                        ct.c_char_p, ct.c_char_p, ct.c_size_t, ct.c_void_p,
                        ct.c_size_t, ct.POINTER(ct.c_size_t)]
    encrypt.restype = ct.c_int
    output = ct.create_string_buffer(len(data) + 16)
    written = ct.c_size_t()
    # kCCEncrypt=0, kCCAlgorithmAES=0, kCCOptionPKCS7Padding=1.
    status = encrypt(0, 0, 1, key, len(key), iv, data, len(data), output,
                     len(output), ct.byref(written))
    if status != 0 or written.value > len(output):
        raise CryptoError("CommonCrypto password encryption failed.")
    return output.raw[:written.value]


def _openssl(data, key, iv, library_path=None):
    library = None
    for name in ([library_path] if library_path else ["libcrypto.so.3", "libcrypto.so.1.1"]):
        try:
            library = ct.CDLL(name)
            break
        except OSError:
            continue
    if library is None:
        raise CryptoError("Password encryption requires OpenSSL libcrypto 3 or 1.1.")
    signatures = {
        "EVP_CIPHER_CTX_new": ([], ct.c_void_p),
        "EVP_CIPHER_CTX_free": ([ct.c_void_p], None),
        "EVP_aes_256_cbc": ([], ct.c_void_p),
        "EVP_EncryptInit_ex": ([ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_char_p, ct.c_char_p], ct.c_int),
        "EVP_EncryptUpdate": ([ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_int), ct.c_char_p, ct.c_int], ct.c_int),
        "EVP_EncryptFinal_ex": ([ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_int)], ct.c_int),
    }
    for name, (args, result) in signatures.items():
        function = getattr(library, name)
        function.argtypes, function.restype = args, result
    context = library.EVP_CIPHER_CTX_new()
    if not context:
        raise CryptoError("Cannot allocate password encryption context.")
    try:
        cipher = library.EVP_aes_256_cbc()
        if not cipher or library.EVP_EncryptInit_ex(context, cipher, None, key, iv) != 1:
            raise CryptoError("Cannot initialize password encryption.")
        output = ct.create_string_buffer(len(data) + 16)
        written, tail = ct.c_int(), ct.c_int()
        if library.EVP_EncryptUpdate(context, output, ct.byref(written), data, len(data)) != 1:
            raise CryptoError("Password encryption failed.")
        if not 0 <= written.value <= len(output) - 16:
            raise CryptoError("Password encryption returned an invalid length.")
        if library.EVP_EncryptFinal_ex(context, ct.byref(output, written.value), ct.byref(tail)) != 1:
            raise CryptoError("Password encryption padding failed.")
        if not 0 <= tail.value <= 16:
            raise CryptoError("Password encryption returned an invalid padding length.")
        return output.raw[:written.value + tail.value]
    finally:
        library.EVP_CIPHER_CTX_free(context)


def encrypt_aes_cbc(data, key, iv):
    if len(key) != 32 or len(iv) != 16 or len(data) > 0x7FFFFFE0:
        raise CryptoError("Invalid AES-256-CBC key, IV or input length.")
    try:
        if sys.platform == "darwin":
            return _commoncrypto(data, key, iv)
        return _openssl(data, key, iv)
    except (OSError, AttributeError) as exc:
        raise CryptoError("System AES encryption provider is unavailable.") from exc
