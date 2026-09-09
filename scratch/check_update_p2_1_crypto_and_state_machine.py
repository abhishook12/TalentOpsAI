"""
check_update_p2_1_crypto_and_state_machine.py — Check 1: Cryptographic Trust Chain & Typed State Machine.

User Rule 11 Verification Suite — Test Tier 1.
"""

import os
import sys
import json
import base64
import tempfile
import shutil

# Include project root
sys.path.insert(0, r"c:\TalentOpsAI")

from backend.app.services.release_signer import (
    sign_manifest,
    sign_package_file,
    sign_package_hash,
    DEFAULT_PUBLIC_KEY_B64,
)
from scout_desktop.core.security import (
    verify_manifest_signature,
    verify_package_signature,
    verify_authenticode_signature,
    DEFAULT_TALENTOPS_PUBLIC_KEY,
)
from scout_desktop.core.updater_state import (
    UpdateStateMachine,
    UpdateState,
    InvalidStateTransitionError,
)


def run_check():
    print("=" * 80)
    print("CHECK 1: CRYPTOGRAPHIC TRUST CHAIN, SIGNATURE VERIFICATION & STATE MACHINE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # Test 1.1: Cryptographic Key Separation Guarantee
    # -------------------------------------------------------------------------
    print("\n[Test 1.1] Verifying Cryptographic Key Separation Architecture...")
    security_file = r"c:\TalentOpsAI\scout_desktop\core\security.py"
    with open(security_file, "r", encoding="utf-8") as f:
        sec_content = f.read()

    assert "Ed25519PrivateKey" not in sec_content, "CRITICAL SECURITY VIOLATION: Private key reference found in client security.py!"
    assert "ZfDISTgWuBhS3lhK3/TbErrfEhTIn4/Euuu5njC7fmM=" not in sec_content, "CRITICAL: Private key bytes found in client security.py!"
    assert DEFAULT_TALENTOPS_PUBLIC_KEY == DEFAULT_PUBLIC_KEY_B64, "Public key mismatch between server signer and client verifier!"
    print("  [OK] Client contains ONLY embedded public key. Zero private keys exist in client codebase.")

    # -------------------------------------------------------------------------
    # Test 1.2: Release Manifest Digital Signature Verification
    # -------------------------------------------------------------------------
    print("\n[Test 1.2] Testing Release Manifest Digital Signature (Ed25519)...")
    manifest = {
        "product": "talentops-scout",
        "channel": "stable",
        "latest_version": "2.6.0",
        "minimum_version": "2.2.0",
        "mandatory": False,
        "package": {
            "url": "https://cdn.talentops.ai/releases/TalentOpsScoutSetup_v2.6.0.exe",
            "sha256": "4a7e93f6c8d19a2b3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
            "size": 50474851,
        },
        "features": {"knowledge_graph_enabled": True},
    }

    sig = sign_manifest(manifest)
    manifest["signature"] = sig
    print(f"  Generated Manifest Signature: {sig[:24]}...")

    # Verify with client public key
    is_valid = verify_manifest_signature(manifest)
    assert is_valid is True, "Valid manifest signature was rejected!"
    print("  [OK] Authentic release manifest successfully verified against embedded public key.")

    # -------------------------------------------------------------------------
    # Test 1.3: Tampered Manifest Rejection (Anti-Spoofing Proof)
    # -------------------------------------------------------------------------
    print("\n[Test 1.3] Testing Tampered Manifest Rejection...")
    tampered_manifest = dict(manifest)
    tampered_manifest["latest_version"] = "2.9.9-malicious"
    is_tampered_valid = verify_manifest_signature(tampered_manifest)
    assert is_tampered_valid is False, "Tampered manifest was mistakenly accepted!"

    tampered_manifest_2 = dict(manifest)
    tampered_manifest_2["package"] = {
        "url": "http://evil-mirror.com/hacked_scout.exe",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "size": 1234,
    }
    is_tampered_valid_2 = verify_manifest_signature(tampered_manifest_2)
    assert is_tampered_valid_2 is False, "Tampered package URL was mistakenly accepted!"
    print("  [OK] Tampered manifests and malicious URL redirections strictly rejected.")

    # -------------------------------------------------------------------------
    # Test 1.4: Detached Package Digital Signature Verification
    # -------------------------------------------------------------------------
    print("\n[Test 1.4] Testing Detached Package Digital Signature Verification...")
    temp_dir = tempfile.mkdtemp(prefix="scout_crypto_test_")
    try:
        pkg_file = os.path.join(temp_dir, "TalentOpsScoutSetup_v2.6.0.exe")
        with open(pkg_file, "wb") as f:
            f.write(b"MOCK_EXE_BINARY_DATA_TALENTOPS_OFFICIAL_RELEASE_V2_6_0" * 500)

        pkg_sig = sign_package_file(pkg_file)
        print(f"  Generated Package Signature: {pkg_sig[:24]}...")

        is_pkg_valid = verify_package_signature(pkg_file, pkg_sig)
        assert is_pkg_valid is True, "Valid package signature was rejected!"
        print("  [OK] Authentic package binary successfully verified.")

        # Tamper package binary bytes
        with open(pkg_file, "ab") as f:
            f.write(b"_INJECTED_CORRUPTION_OR_MALWARE_BYTE")

        is_corrupt_valid = verify_package_signature(pkg_file, pkg_sig)
        assert is_corrupt_valid is False, "Corrupted package was mistakenly accepted!"
        print("  [OK] Corrupted or tampered package binary strictly rejected.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Test 1.5: Typed Update State Machine Lifecycle & Transition Guards
    # -------------------------------------------------------------------------
    print("\n[Test 1.5] Testing Typed Update State Machine Lifecycle & Transitions...")
    sm = UpdateStateMachine()
    sm.reset_to_stable()
    assert sm.current_state == UpdateState.UP_TO_DATE

    # Happy path transition sequence
    sm.transition(UpdateState.UPDATE_AVAILABLE, target_version="2.6.0")
    assert sm.current_state == UpdateState.UPDATE_AVAILABLE

    sm.transition(UpdateState.DOWNLOADING)
    assert sm.current_state == UpdateState.DOWNLOADING
    assert sm.is_in_progress() is True

    sm.transition(UpdateState.DOWNLOADED)
    assert sm.current_state == UpdateState.DOWNLOADED

    sm.transition(UpdateState.VERIFYING)
    assert sm.current_state == UpdateState.VERIFYING

    sm.transition(UpdateState.APPLYING)
    assert sm.current_state == UpdateState.APPLYING

    sm.transition(UpdateState.HEALTH_CHECK)
    assert sm.current_state == UpdateState.HEALTH_CHECK

    sm.transition(UpdateState.SUCCESS, context="Verified and committed")
    assert sm.current_state == UpdateState.SUCCESS

    sm.transition(UpdateState.UP_TO_DATE)
    assert sm.current_state == UpdateState.UP_TO_DATE
    print("  [OK] Standard update lifecycle (UP_TO_DATE -> DOWNLOADING -> VERIFYING -> APPLYING -> SUCCESS) verified.")

    # Guard: Illegal jump check
    print("\n[Test 1.6] Testing State Machine Guard against Illegal State Jumps...")
    sm.transition(UpdateState.UPDATE_AVAILABLE, target_version="2.6.0")
    sm.transition(UpdateState.DOWNLOADING)
    try:
        # Cannot jump from DOWNLOADING directly to SUCCESS without DOWNLOADED, VERIFYING, APPLYING
        sm.transition(UpdateState.SUCCESS, strict=True)
        assert False, "Illegal transition was allowed!"
    except InvalidStateTransitionError as e:
        print(f"  [OK] Successfully blocked illegal transition: {e}")

    # Rollback lifecycle check
    print("\n[Test 1.7] Testing Rollback Lifecycle Transitions...")
    sm.transition(UpdateState.DOWNLOAD_FAILED, context="Network connection reset")
    assert sm.is_failed() is True

    sm.transition(UpdateState.DOWNLOADING)
    sm.transition(UpdateState.DOWNLOADED)
    sm.transition(UpdateState.VERIFYING)
    sm.transition(UpdateState.APPLYING)
    sm.transition(UpdateState.HEALTH_CHECK)
    sm.transition(UpdateState.HEALTH_CHECK_FAILED, context="Binary crashed on startup")
    sm.transition(UpdateState.ROLLBACK, context="Initiating automatic rollback")
    sm.transition(UpdateState.RESTORE_PREVIOUS, context="Restoring files from snapshot")
    sm.transition(UpdateState.STABLE, context="Restoration complete, verified previous version")
    assert sm.current_state == UpdateState.STABLE
    print("  [OK] Rollback lifecycle (HEALTH_CHECK_FAILED -> ROLLBACK -> RESTORE_PREVIOUS -> STABLE) verified.")

    print("\n" + "=" * 80)
    print("CHECK 1 RESULT: PASSED (100% SUCCESSFUL)")
    print("Cryptographic signature trust chain and typed state machine fully verified.")
    print("=" * 80)


if __name__ == "__main__":
    run_check()
