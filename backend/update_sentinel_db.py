import sqlite3

c = sqlite3.connect('dev.db')

try:
    c.execute('ALTER TABLE recruiters ADD COLUMN quality_score INTEGER DEFAULT 0')
    c.execute('CREATE INDEX ix_recruiters_quality_score ON recruiters (quality_score)')
except Exception as e:
    print('quality_score:', e)

try:
    c.execute('ALTER TABLE recruiters ADD COLUMN missing_fields TEXT DEFAULT "{}"')
except Exception as e:
    print('missing_fields:', e)

try:
    c.execute('ALTER TABLE recruiters ADD COLUMN sentinel_status VARCHAR(50) DEFAULT "Pending"')
    c.execute('CREATE INDEX ix_recruiters_sentinel_status ON recruiters (sentinel_status)')
except Exception as e:
    print('sentinel_status:', e)

try:
    c.execute('ALTER TABLE recruiters ADD COLUMN last_verified_at TIMESTAMP')
except Exception as e:
    print('last_verified_at:', e)

try:
    c.execute('''
        CREATE TABLE sentinel_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER NOT NULL,
            field_changed VARCHAR(100) NOT NULL,
            previous_value TEXT,
            new_value TEXT,
            reason TEXT NOT NULL,
            confidence FLOAT DEFAULT 1.0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE
        )
    ''')
    c.execute('CREATE INDEX ix_sentinel_audit_logs_recruiter_id ON sentinel_audit_logs (recruiter_id)')
except Exception as e:
    print('sentinel_audit_logs:', e)

try:
    c.execute('''
        CREATE TABLE sentinel_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status VARCHAR(50) DEFAULT 'Idle',
            total_profiles INTEGER DEFAULT 0,
            profiles_analyzed INTEGER DEFAULT 0,
            profiles_repaired INTEGER DEFAULT 0,
            current_task_description VARCHAR(255),
            last_processed_id INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('INSERT INTO sentinel_state (id, status) VALUES (1, "Idle")')
except Exception as e:
    print('sentinel_state:', e)

c.commit()
c.close()
print('Database updated successfully!')
