import os
import shutil
import time
import logging
from datetime import datetime
from threading import Thread
from app.database import DATABASE_URL

logger = logging.getLogger("talentops.backup")

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")

def create_backup():
    """Create a backup of the SQLite database."""
    if not DATABASE_URL.startswith("sqlite:///"):
        logger.info("Not a SQLite database, skipping automated file backup.")
        return False
        
    os.makedirs(BACKUP_DIR, exist_ok=True)
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found at {db_path}")
        return False
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"talentops_{timestamp}.sqlite")
    
    try:
        shutil.copy2(db_path, backup_file)
        logger.info(f"Database backed up successfully to {backup_file}")
        
        # Cleanup old backups (keep last 7)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("talentops_") and f.endswith(".sqlite")])
        if len(backups) > 7:
            for old_backup in backups[:-7]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
                logger.info(f"Removed old backup: {old_backup}")
                
        return True
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return False

def _backup_loop(interval_hours=24):
    """Background loop to periodically run backups."""
    logger.info(f"Starting automated backup service (interval: {interval_hours}h)")
    while True:
        try:
            # Sleep first so we don't immediately backup on restart if we just backed up
            time.sleep(interval_hours * 3600)
            create_backup()
        except Exception as e:
            logger.error(f"Error in backup thread: {e}")
            time.sleep(300) # Sleep 5m on error before retrying

def start_backup_service(interval_hours=24):
    """Start the backup service in a background thread."""
    thread = Thread(target=_backup_loop, args=(interval_hours,), daemon=True)
    thread.start()
    return thread
