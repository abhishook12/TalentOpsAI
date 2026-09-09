"""
release_signer.py — Backend Server-Side Release Signing Service.

Uses Ed25519 asymmetric cryptography to sign:
1. Release manifests (canonical JSON representation)
2. Installer binaries & update packages (SHA-256 digest)

SECURITY NOTICE:
The private signing key is stored in environment variables / secure KMS on the backend server.
It is NEVER bundled into client installations or the scout_desktop client codebase.
"""

import os
import json
import base64
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger("talentops.release_signer")

# Development fallback private key (32-byte Ed25519 in Base64)
# In production, this is overridden by TALENTOPS_RELEASE_SIGNING_KEY env variable.
DEV_SIGNING_KEY_B64 = "ZfDISTgWuBhS3lhK3/TbErrfEhTIn4/Euuu5njC7fmM="
DEFAULT_PUBLIC_KEY_B64 = "a3Q6eCkxf410FpPMJU1yNm6vLQ4vsyCXHzPT4d64cRc="


def get_private_key(priv_key_b64: Optional[str] = None):
    """Loads the Ed25519 private key from param, env var, or dev fallback."""
    if not HAS_CRYPTOGRAPHY:
        raise RuntimeError("cryptography library not installed!")

    key_str = priv_key_b64 or os.environ.get("TALENTOPS_RELEASE_SIGNING_KEY") or DEV_SIGNING_KEY_B64
    raw_bytes = base64.b64decode(key_str)
    return ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)


def canonicalize_manifest(manifest: Dict[str, Any]) -> bytes:
    """Produces canonical JSON bytes for deterministic digital signature."""
    clean = {
        k: v for k, v in manifest.items()
        if k not in ("signature", "manifest_signature", "package_signature")
    }
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sign_manifest(manifest: Dict[str, Any], priv_key_b64: Optional[str] = None) -> str:
    """Signs a release manifest dictionary and returns the base64 digital signature."""
    private_key = get_private_key(priv_key_b64)
    data_bytes = canonicalize_manifest(manifest)
    signature_bytes = private_key.sign(data_bytes)
    sig_b64 = base64.b64encode(signature_bytes).decode("ascii")
    logger.info("Signed manifest (length %d bytes) -> signature: %s...", len(data_bytes), sig_b64[:16])
    return sig_b64


def sign_package_file(file_path: str, priv_key_b64: Optional[str] = None) -> str:
    """Signs the SHA-256 digest of an installer binary or package."""
    private_key = get_private_key(priv_key_b64)
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    digest = hasher.digest()
    sig_bytes = private_key.sign(digest)
    return base64.b64encode(sig_bytes).decode("ascii")


def sign_package_hash(sha256_hex: str, priv_key_b64: Optional[str] = None) -> str:
    """Signs a precomputed SHA-256 hex string digest."""
    private_key = get_private_key(priv_key_b64)
    digest = bytes.fromhex(sha256_hex)
    sig_bytes = private_key.sign(digest)
    return base64.b64encode(sig_bytes).decode("ascii")
