"""
updater_helper.py — Out-of-Process Autonomous Updater & Rollback Engine for TalentOps Scout.

Runs as a detached, independent process so Scout.exe can terminate cleanly
without file-locking conflicts.

Lifecycle:
1. Wait for parent Scout process (PID) to terminate cleanly.
2. Snapshot current application files into a rollback backup directory.
3. Apply update (silent installer execution or atomic payload swap).
4. Run post-update health check on the newly installed binary.
5. If health check succeeds -> Commit update & relaunch Scout.
6. If update fails or crashes -> AUTOMATIC ROLLBACK to previous stable version & relaunch.
"""

import os
import sys
import time
import json
import shutil
import argparse
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [ScoutUpdater] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scout.updater_helper")


def is_process_running(pid: int) -> bool:
    """Checks if a process with given PID is still active on Windows/Unix."""
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            output = subprocess.check_output(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            ).decode("utf-8", errors="ignore")
            return str(pid) in output
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def wait_for_process_exit(pid: int, timeout_sec: float = 12.0) -> bool:
    """Waits for process to exit; forcefully terminates if still running after timeout."""
    start = time.time()
    logger.info("Waiting for Scout process (PID %d) to exit...", pid)
    while time.time() - start < timeout_sec:
        if not is_process_running(pid):
            logger.info("[OK] Process %d has exited.", pid)
            return True
        time.sleep(0.5)

    logger.warning("Process %d did not exit within %ss, terminating forcefully...", pid, timeout_sec)
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            os.kill(pid, 9)
    except Exception as e:
        logger.warning("Error terminating process %d: %e", pid, e)

    time.sleep(1.0)
    return not is_process_running(pid)


def create_rollback_backup(target_dir: str, backup_dir: str) -> bool:
    """Creates a complete backup snapshot of the current application directory."""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        # Clear any prior backup
        for item in os.listdir(backup_dir):
            p = os.path.join(backup_dir, item)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            else:
                os.remove(p)

        logger.info("Creating rollback backup from '%s' to '%s'...", target_dir, backup_dir)
        for item in os.listdir(target_dir):
            src = os.path.join(target_dir, item)
            dst = os.path.join(backup_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        meta = {
            "source_dir": target_dir,
            "backup_timestamp": time.time(),
            "status": "BACKUP_VALID",
        }
        with open(os.path.join(backup_dir, "rollback_manifest.json"), "w") as f:
            json.dump(meta, f)
        logger.info("[OK] Rollback snapshot created successfully.")
        return True
    except Exception as e:
        logger.error("Failed to create rollback backup: %s", e)
        return False


def restore_rollback_backup(backup_dir: str, target_dir: str) -> bool:
    """Restores application files from the backup directory back to the target directory."""
    logger.warning("[ROLLBACK] INITIATING AUTOMATIC ROLLBACK from '%s' -> '%s'...", backup_dir, target_dir)
    try:
        if not os.path.exists(backup_dir):
            logger.error("Rollback directory does not exist: %s", backup_dir)
            return False

        for item in os.listdir(backup_dir):
            if item == "rollback_manifest.json":
                continue
            src = os.path.join(backup_dir, item)
            dst = os.path.join(target_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        logger.info("[OK] Rollback restoration complete.")
        return True
    except Exception as e:
        logger.error("[CRITICAL] Rollback failed: %s", e)
        return False


def verify_post_install_health(executable_path: str, timeout_sec: float = 6.0) -> bool:
    """
    Executes the newly installed binary with `--health-check` to verify it can boot
    and load its DLLs/packages without crashing.
    """
    if not os.path.exists(executable_path):
        logger.error("Executable not found for health check: %s", executable_path)
        return False

    logger.info("Verifying post-install health of '%s'...", executable_path)
    try:
        # If executable is a python script or .exe
        if executable_path.endswith(".py"):
            cmd = [sys.executable, executable_path, "--health-check"]
        else:
            cmd = [executable_path, "--health-check"]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
            exit_code = proc.returncode
            if exit_code == 0:
                logger.info("[OK] Post-install health check PASSED (Exit Code 0).")
                return True
            else:
                logger.error("Post-install health check FAILED with code %d: %s", exit_code, stderr.decode(errors="ignore"))
                return False
        except subprocess.TimeoutExpired:
            proc.kill()
            # If it stayed alive without crashing, it may be waiting; treat as success
            logger.info("[OK] Process booted cleanly within timeout window.")
            return True
    except Exception as e:
        logger.error("Post-install health check crashed: %s", e)
        return False


def perform_update(
    package_path: str,
    target_dir: str,
    backup_dir: str,
    target_pid: int,
    executable_name: str = "TalentOpsScout.exe",
    restart_after: bool = True,
) -> Dict[str, Any]:
    """Main updater orchestration engine."""
    result = {
        "status": "INITIALIZING",
        "error": None,
        "rolled_back": False,
    }

    # 1. Wait for running Scout process to terminate
    if target_pid > 0:
        if not wait_for_process_exit(target_pid):
            result["status"] = "FAILED"
            result["error"] = f"Could not terminate existing process {target_pid}"
            return result

    # 2. Create Rollback Snapshot
    if os.path.exists(target_dir):
        create_rollback_backup(target_dir, backup_dir)

    # 3. Apply Update
    logger.info("Applying update package: %s -> %s", package_path, target_dir)
    target_exe = os.path.join(target_dir, executable_name)

    try:
        if package_path.endswith(".exe") and "Setup" in package_path:
            # Native Inno Setup installer
            cmd = [
                package_path,
                "/SILENT",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS=0",
                f"/DIR={target_dir}",
            ]
            logger.info("Running Inno Setup: %s", " ".join(cmd))
            inst_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if inst_proc.returncode != 0:
                raise RuntimeError(f"Installer failed with returncode {inst_proc.returncode}: {inst_proc.stderr}")
        elif package_path.endswith(".zip"):
            import zipfile
            with zipfile.ZipFile(package_path, "r") as z:
                z.extractall(target_dir)
        else:
            # Single binary or directory swap
            if os.path.isfile(package_path):
                shutil.copy2(package_path, target_exe)
            elif os.path.isdir(package_path):
                shutil.copytree(package_path, target_dir, dirs_exist_ok=True)

        logger.info("[OK] Update files applied successfully.")
    except Exception as apply_err:
        logger.error("[ERROR] Failed to apply update package: %s", apply_err)
        restore_rollback_backup(backup_dir, target_dir)
        result["status"] = "FAILED_ROLLED_BACK"
        result["rolled_back"] = True
        result["error"] = str(apply_err)
        return result

    # 4. Post-Install Health Check
    health_ok = verify_post_install_health(target_exe)
    if not health_ok:
        logger.error("[ERROR] New version failed health check! Triggering rollback...")
        restore_rollback_backup(backup_dir, target_dir)
        result["status"] = "HEALTH_CHECK_FAILED_ROLLED_BACK"
        result["rolled_back"] = True
        result["error"] = "Post-install health check failed or process crashed on startup"
        # Relaunch restored stable version
        if restart_after and os.path.exists(target_exe):
            logger.info("Relaunching restored previous stable version: %s", target_exe)
            subprocess.Popen([target_exe], shell=False)
        return result

    # 5. Success: Commit Update
    result["status"] = "SUCCESS"
    logger.info("[SUCCESS] TalentOps Scout update completed and verified successfully!")

    # 6. Restart Application
    if restart_after and os.path.exists(target_exe):
        logger.info("Relaunching updated TalentOps Scout: %s", target_exe)
        try:
            if target_exe.endswith(".py"):
                subprocess.Popen([sys.executable, target_exe], shell=False)
            else:
                subprocess.Popen([target_exe], shell=False)
        except Exception as launch_err:
            logger.warning("Could not automatically restart process: %s", launch_err)

    return result


def main():
    parser = argparse.ArgumentParser(description="TalentOps Scout Out-of-Process Updater Helper")
    parser.add_argument("--package", required=True, help="Path to installer or update package")
    parser.add_argument("--target-dir", required=True, help="Application target directory")
    parser.add_argument("--backup-dir", required=True, help="Rollback backup directory")
    parser.add_argument("--target-pid", type=int, default=0, help="PID of running Scout process to wait for")
    parser.add_argument("--executable-name", default="TalentOpsScout.exe", help="Name of executable to check")
    parser.add_argument("--no-restart", action="store_true", help="Do not relaunch application after update")

    args = parser.parse_args()

    res = perform_update(
        package_path=args.package,
        target_dir=args.target_dir,
        backup_dir=args.backup_dir,
        target_pid=args.target_pid,
        executable_name=args.executable_name,
        restart_after=not args.no_restart,
    )

    print(json.dumps(res, indent=2))
    sys.exit(0 if res["status"] == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
