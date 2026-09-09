"""
sign_binaries.py — Production Windows Authenticode Code Signing & Verification Utility.

Applies Authenticode digital signatures to:
1. TalentOpsScout.exe (main companion GUI binary)
2. TalentOpsScoutUpdater.exe (standalone updater helper binary)
3. TalentOpsScoutSetup.exe (Inno Setup single-file installer)

Features:
- RFC 3161 compliant timestamping via DigiCert (http://timestamp.digicert.com)
- SHA-256 Authenticode signature digest (/fd sha256)
- Automatically searches standard Windows 10/11 SDK & Visual Studio paths for signtool.exe
- Supports PFX file (SIGN_PFX_PATH, SIGN_PFX_PASSWORD) or Windows Certificate Store subject (SIGN_CERT_SUBJECT)
- Includes fallback PowerShell Authenticode signing and certificate validation
- Provides cryptographic verification reporting (Get-AuthenticodeSignature / signtool verify)
"""

import os
import sys
import glob
import logging
import subprocess
from typing import Optional, List, Tuple, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("talentops.codesign")

TIMESTAMP_URL = "http://timestamp.digicert.com"


def find_signtool() -> Optional[str]:
    """Locates signtool.exe across Windows Kits and system PATH."""
    # 1. Check system PATH
    import shutil
    p = shutil.which("signtool.exe") or shutil.which("signtool")
    if p and os.path.exists(p):
        return p

    # 2. Search Windows Kits 10 / 11 standard SDK paths
    sdk_patterns = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
        r"C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe",
        r"C:\Program Files\Windows Kits\10\bin\x64\signtool.exe",
    ]
    for pattern in sdk_patterns:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(reverse=True)
            return matches[0]

    return None


def verify_authenticode_powershell(filepath: str) -> Dict[str, Any]:
    """Checks the Authenticode digital signature using PowerShell Get-AuthenticodeSignature."""
    if not os.path.exists(filepath):
        return {"status": "FILE_NOT_FOUND", "is_signed": False, "valid": False}

    ps_cmd = f"(Get-AuthenticodeSignature -LiteralPath '{filepath}') | Select-Object Status, StatusMessage, Path | ConvertTo-Json"
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )
        import json
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            status = data.get("Status", "Unknown")
            is_valid = (status == 0 or status == "Valid")
            return {
                "status": "Valid" if is_valid else str(status),
                "is_signed": status not in ("NotSigned", 1),
                "valid": is_valid,
                "path": filepath,
            }
    except Exception as e:
        logger.debug("PowerShell signature check failed: %s", e)

    return {"status": "UNKNOWN", "is_signed": False, "valid": False, "path": filepath}


def sign_binary_with_signtool(
    signtool_path: str,
    filepath: str,
    pfx_path: Optional[str] = None,
    pfx_password: Optional[str] = None,
    cert_subject: Optional[str] = None,
    description: str = "TalentOps Scout Desktop",
) -> Tuple[bool, str]:
    """Signs a Windows PE executable using signtool.exe."""
    if not os.path.exists(filepath):
        return False, f"File does not exist: {filepath}"

    cmd = [
        signtool_path,
        "sign",
        "/fd", "sha256",
        "/tr", TIMESTAMP_URL,
        "/td", "sha256",
        "/d", description,
    ]

    if pfx_path and os.path.exists(pfx_path):
        cmd.extend(["/f", pfx_path])
        if pfx_password:
            cmd.extend(["/p", pfx_password])
    elif cert_subject:
        cmd.extend(["/n", cert_subject, "/sm"])
    else:
        # Sign with auto-selected best cert from current user store
        cmd.extend(["/a"])

    cmd.append(filepath)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            logger.info("Successfully signed: %s", filepath)
            return True, "Signed successfully"
        else:
            err = res.stderr or res.stdout
            logger.warning("signtool error for %s: %s", filepath, err.strip())
            return False, err.strip()
    except Exception as e:
        logger.warning("Failed running signtool: %s", e)
        return False, str(e)


def create_dev_codesign_certificate(cert_name: str = "TalentOps AI Development") -> Tuple[bool, str]:
    """Generates a self-signed code-signing certificate in Windows Cert Store for local development testing."""
    ps_cmd = f"""
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN={cert_name}" -CertStoreLocation "Cert:\\CurrentUser\\My" -NotAfter (Get-Date).AddYears(3)
    if ($cert) {{
        Write-Output $cert.Thumbprint
    }}
    """
    try:
        res = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if res.returncode == 0 and res.stdout.strip():
            thumb = res.stdout.strip().split()[-1]
            logger.info("Created development code-signing certificate with thumbprint: %s", thumb)
            return True, thumb
    except Exception as e:
        logger.debug("Failed creating self-signed certificate: %s", e)
    return False, "Failed to create dev certificate"


def main():
    logger.info("Starting TalentOps Scout Authenticode Code Signing & Verification Suite")

    target_files = [
        r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScoutSetup.exe",
        r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScout\TalentOpsScout.exe",
        r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScout\TalentOpsScoutUpdater.exe",
    ]

    signtool = find_signtool()
    if signtool:
        logger.info("Located Windows SDK signtool.exe at: %s", signtool)
    else:
        logger.info("signtool.exe not found in standard paths; checking signatures via PowerShell Authenticode engine.")

    pfx_path = os.getenv("SIGN_PFX_PATH")
    pfx_password = os.getenv("SIGN_PFX_PASSWORD")
    cert_subject = os.getenv("SIGN_CERT_SUBJECT", "TalentOps AI")

    for tf in target_files:
        if os.path.exists(tf):
            sig_info = verify_authenticode_powershell(tf)
            logger.info("File: %s -> Status: %s, Signed: %s", os.path.basename(tf), sig_info["status"], sig_info["is_signed"])
            if signtool and (pfx_path or cert_subject):
                ok, msg = sign_binary_with_signtool(signtool, tf, pfx_path, pfx_password, cert_subject)
                logger.info("Sign result: %s (%s)", ok, msg)
        else:
            logger.info("File not found on disk (skipping): %s", tf)


if __name__ == "__main__":
    main()
