from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os
from pathlib import Path


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32


def _to_blob(data: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    buffer = (ctypes.c_byte * len(data))(*data)
    blob = DATA_BLOB(len(data), buffer)
    return blob, buffer


def _from_blob(blob: DATA_BLOB) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


def _protect(data: bytes) -> bytes:
    in_blob, _ = _to_blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "shopping-feed-ai-v2",
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise OSError("CryptProtectData selhalo.")
    try:
        return _from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _unprotect(data: bytes) -> bytes:
    in_blob, _ = _to_blob(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise OSError("CryptUnprotectData selhalo.")
    try:
        return _from_blob(out_blob)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _secret_file() -> Path:
    base_dir = Path(os.getenv("LOCALAPPDATA", "")) if os.getenv("LOCALAPPDATA") else Path("data")
    return base_dir / "shopping-feed-ai-v2" / "openai_api_key.dpapi"


def has_saved_api_key() -> bool:
    return _secret_file().exists()


def save_api_key(api_key: str) -> None:
    target = _secret_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _protect(api_key.encode("utf-8"))
    target.write_text(base64.b64encode(encrypted).decode("ascii"), encoding="ascii")


def load_api_key() -> str:
    target = _secret_file()
    if not target.exists():
        return ""
    encrypted = base64.b64decode(target.read_text(encoding="ascii"))
    return _unprotect(encrypted).decode("utf-8")


def delete_api_key() -> None:
    target = _secret_file()
    if target.exists():
        target.unlink()
