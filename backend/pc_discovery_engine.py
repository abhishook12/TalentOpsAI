import os
import glob
import hashlib
import json
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pc_discovery")

TARGET_ROOTS = [
    "c:/TalentOpsAI",
    "c:/Users/User/Desktop",
    "c:/Users/User/Downloads",
    "c:/Users/User/Documents",
    "D:/"
]

EXCLUDE_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".gemini", "AppData", "$RECYCLE.BIN", "System Volume Information"}

def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.warning(f"Could not hash {filepath}: {e}")
        return ""

def discover_pc_workbooks() -> Dict[str, Dict]:
    logger.info("=========================================================")
    logger.info("LAUNCHING HUMONGOUS PC-WIDE DISCOVERY SWARM (C:\\ & D:\\)")
    logger.info("=========================================================")
    
    discovered_files = []
    for root in TARGET_ROOTS:
        if not os.path.exists(root):
            continue
        logger.info(f"Scanning target root: {root} ...")
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
            
            for f in filenames:
                ext = f.lower()
                if ext.endswith(".xlsx") or ext.endswith(".csv") or ext.endswith(".xls"):
                    full_path = os.path.join(dirpath, f)
                    try:
                        sz = os.path.getsize(full_path)
                        if sz > 100: # Skip empty 0-byte placeholders
                            discovered_files.append((full_path, sz))
                    except Exception:
                        pass

    logger.info(f"Raw discovery: found {len(discovered_files)} candidate workbook files across PC.")
    logger.info("Computing SHA-256 checksums to eliminate duplicate file copies...")
    
    unique_manifest = {}
    seen_hashes = {}
    
    for filepath, size_bytes in discovered_files:
        file_hash = calculate_sha256(filepath)
        if not file_hash:
            continue
            
        if file_hash in seen_hashes:
            logger.debug(f"Skipping duplicate file copy: {filepath} (identical to {seen_hashes[file_hash]})")
        else:
            seen_hashes[file_hash] = filepath
            unique_manifest[filepath] = {
                "sha256": file_hash,
                "size_mb": round(size_bytes / (1024 * 1024), 3),
                "extension": os.path.splitext(filepath)[1].lower()
            }
            
    logger.info(f"DEDUPLICATION VICTORY: Reduced {len(discovered_files)} raw files -> {len(unique_manifest)} UNIQUE canonical workbooks!")
    total_mb = sum(m["size_mb"] for m in unique_manifest.values())
    logger.info(f"Total Unique Payload Footprint: {total_mb:.2f} MB")
    
    out_path = "pc_unique_manifest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unique_manifest, f, indent=2)
    logger.info(f"Saved unique workbook inventory to {out_path}.")
    return unique_manifest

if __name__ == "__main__":
    discover_pc_workbooks()
