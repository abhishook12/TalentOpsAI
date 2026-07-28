import sqlite3

def migrate():
    print("Migrating dev.db...")
    conn = sqlite3.connect('dev.db')
    cursor = conn.cursor()
    
    # Create trusted_devices table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trusted_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id_hash VARCHAR(255) UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        browser VARCHAR(255),
        os VARCHAR(255),
        device_name VARCHAR(255),
        last_login DATETIME,
        status VARCHAR(50) DEFAULT 'Pending',
        approved_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(approved_by) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    
    # Check if trusted_device_id exists in sessions
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'trusted_device_id' not in columns:
        print("Adding trusted_device_id to sessions...")
        cursor.execute('ALTER TABLE sessions ADD COLUMN trusted_device_id INTEGER REFERENCES trusted_devices(id) ON DELETE CASCADE')
    
    # Also we need to make sure index is created for device_id_hash
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_trusted_devices_device_id_hash ON trusted_devices(device_id_hash)")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
