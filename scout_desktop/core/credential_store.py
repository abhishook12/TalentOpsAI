"""Small Windows DPAPI wrapper for Scout's locally persisted credentials.

Only the interactive Windows account that stored a value can decrypt it.  Scout
keeps non-secret device metadata in JSON, but never writes a raw access token.
"""

from __future__ import annotations

import base64
import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Optional

logger = logging.getLogger("scout.credential_store")

_PREFIX = "dpapi:v1:"


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def protect_token(token: str) -> Optional[str]:
    """Encrypt a token for the current Windows account, returning a portable string."""
    if not token or sys.platform != "win32":
        return None
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        source, _source_buffer = _blob(token.encode("utf-8"))
        protected = _DataBlob()
        if not crypt32.CryptProtectData(ctypes.byref(source), "TalentOps Scout token", None, None, None, 0, ctypes.byref(protected)):
            raise ctypes.WinError()
        try:
            raw = ctypes.string_at(protected.pbData, protected.cbData)
            return _PREFIX + base64.b64encode(raw).decode("ascii")
        finally:
            kernel32.LocalFree(protected.pbData)
    except Exception as exc:
        logger.warning("Could not protect Scout credential with Windows DPAPI: %s", exc)
        return None


def unprotect_token(value: str) -> Optional[str]:
    """Decrypt a DPAPI token stored by :func:`protect_token`."""
    if not value or not value.startswith(_PREFIX) or sys.platform != "win32":
        return None
    try:
        encrypted = base64.b64decode(value[len(_PREFIX):].encode("ascii"), validate=True)
        source, _source_buffer = _blob(encrypted)
        plain = _DataBlob()
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(plain)):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(plain.pbData, plain.cbData).decode("utf-8")
        finally:
            kernel32.LocalFree(plain.pbData)
    except Exception as exc:
        logger.warning("Could not decrypt Scout credential with Windows DPAPI: %s", exc)
        return None
