"""
core/security.py — Cryptographic Signature Verification & Trust Chain for TalentOps Scout.

Trust Chain Architecture:
1. TalentOpsAI Private Signing Key (Isolated on Build/Release Server ONLY)
   -> Signs Release Manifest & Installer Binary
2. Embedded Public Key (In Scout Desktop Client)
   -> Cryptographically verifies authenticity of Manifest & Package
3. SHA-256 Integrity Verification
   -> Verifies package byte integrity against tamper-resistant digest
4. Windows Authenticode Verification
   -> Verifies binary certificate on Windows platforms

CRITICAL SECURITY RULE:
The private signing key MUST NEVER exist inside the Scout repository or desktop application.
Only the embedded public key is distributed with Scout clients.
"""

import os
import sys
import json
import base64
import logging
import hashlib
import subprocess
from typing import Optional, Dict, Any

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger("scout.security")

# Embedded TalentOpsAI Release Verification Public Key (Ed25519 - 32 bytes Base64)
# Corresponding private key is kept securely on the release server and NEVER shipped.
DEFAULT_TALENTOPS_PUBLIC_KEY = "a3Q6eCkxf410FpPMJU1yNm6vLQ4vsyCXHzPT4d64cRc="


def canonicalize_json(data: Dict[str, Any]) -> bytes:
    """
    Produces deterministic canonical JSON bytes with sorted keys and no whitespace.
    Excludes signature fields to enable self-verifying payload structures.
    """
    clean_dict = {
        k: v for k, v in data.items()
        if k not in ("signature", "manifest_signature", "package_signature")
    }
    return json.dumps(clean_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def verify_manifest_signature(
    manifest: Dict[str, Any],
    signature_b64: Optional[str] = None,
    public_key_b64: Optional[str] = None,
) -> bool:
    """
    Verifies that the release manifest was signed by TalentOpsAI's private signing key.
    Rejects tampered manifests or counterfeit update servers.
    """
    if not HAS_CRYPTOGRAPHY:
        logger.error("Security library 'cryptography' is not installed! Cannot verify signature.")
        return False

    sig_to_verify = signature_b64 or manifest.get("signature") or manifest.get("manifest_signature")
    if not sig_to_verify:
        logger.warning("Manifest has no cryptographic signature attached. Signature verification FAILED.")
        return False

    pub_key_str = public_key_b64 or DEFAULT_TALENTOPS_PUBLIC_KEY

    try:
        raw_pub_bytes = base64.b64decode(pub_key_str)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub_bytes)

        raw_sig = base64.b64decode(sig_to_verify)
        canonical_bytes = canonicalize_json(manifest)

        public_key.verify(raw_sig, canonical_bytes)
        logger.info("[OK] Manifest signature verified successfully with TalentOps public key.")
        return True
    except InvalidSignature:
        logger.error("[SECURITY ALERT] Invalid manifest signature! The update manifest has been tampered with or is counterfeit!")
        return False
    except Exception as e:
        logger.error("Error verifying manifest signature: %s", e)
        return False


def verify_package_signature(
    package_path: str,
    package_signature_b64: Optional[str] = None,
    public_key_b64: Optional[str] = None,
) -> bool:
    """
    Verifies the detached cryptographic signature of the downloaded installer package.
    Signs the SHA-256 digest of the binary package.
    """
    if not HAS_CRYPTOGRAPHY:
        logger.error("Security library 'cryptography' is not installed! Cannot verify package signature.")
        return False

    if not package_signature_b64:
        logger.warning("No package signature provided for binary: %s", package_path)
        return False

    if not os.path.exists(package_path):
        logger.error("Package file does not exist for signature check: %s", package_path)
        return False

    pub_key_str = public_key_b64 or DEFAULT_TALENTOPS_PUBLIC_KEY

    try:
        # Compute SHA-256 of file
        hasher = hashlib.sha256()
        with open(package_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        file_sha256_bytes = hasher.digest()

        raw_pub_bytes = base64.b64decode(pub_key_str)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub_bytes)

        raw_sig = base64.b64decode(package_signature_b64)
        public_key.verify(raw_sig, file_sha256_bytes)
        logger.info("[OK] Package cryptographic signature verified successfully.")
        return True
    except InvalidSignature:
        logger.error("[SECURITY ALERT] Package signature mismatch! Binary is untrusted or corrupted.")
        return False
    except Exception as e:
        logger.error("Package signature verification error: %s", e)
        return False


def verify_authenticode_signature(exe_path: str) -> Dict[str, Any]:
    """
    Verifies Windows Authenticode signature via PowerShell Get-AuthenticodeSignature.
    Returns status dict: {'valid': bool, 'status': str, 'signer': Optional[str]}
    """
    if sys.platform != "win32" or not os.path.exists(exe_path):
        return {"valid": True, "status": "SKIPPED_NON_WINDOWS", "signer": None}

    try:
        script = f'(Get-AuthenticodeSignature "{exe_path}") | Select-Object -Property Status, StatusMessage | ConvertTo-Json'
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8.0,
        )
        if res.returncode == 0 and res.stdout.strip():
            info = json.loads(res.stdout.strip())
            status = info.get("Status", 0)
            is_valid = (status == 0 or str(status).lower() == "valid")
            return {
                "valid": is_valid,
                "status": str(status),
                "status_message": info.get("StatusMessage", ""),
            }
    except Exception as e:
        logger.debug("Authenticode check query failed: %s", e)

    return {"valid": False, "status": "UNKNOWN_ERROR", "signer": None}
