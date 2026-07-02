import sqlite3
import sys

def main():
    conn = sqlite3.connect('dev.db')
    c = conn.cursor()
    
    queries = [
        """
        CREATE TABLE IF NOT EXISTS company_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
            alias_name VARCHAR(255) NOT NULL,
            alias_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS company_email_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER REFERENCES companies(company_id) ON DELETE CASCADE,
            domain VARCHAR(255) NOT NULL,
            pattern VARCHAR(100) NOT NULL,
            verified_example_count INTEGER DEFAULT 0,
            match_percentage NUMERIC(5,2),
            confidence VARCHAR(20),
            source VARCHAR(50),
            last_verified_at TIMESTAMP,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS email_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER REFERENCES recruiters(recruiter_id) ON DELETE CASCADE,
            candidate_email VARCHAR(255) NOT NULL,
            domain VARCHAR(255) NOT NULL,
            pattern VARCHAR(100),
            confidence_score INTEGER,
            status VARCHAR(50) DEFAULT 'generated',
            evidence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP,
            rejection_reason TEXT
        );
        """
    ]
    
    # SQLite ALTER TABLE ADD COLUMN does not support IF NOT EXISTS natively in Python sqlite3 easily without querying pragma, so we'll just try each one and ignore errors if they already exist.
    alter_queries = [
        "ALTER TABLE recruiters ADD COLUMN email_status VARCHAR(50) DEFAULT 'unknown';",
        "ALTER TABLE recruiters ADD COLUMN email_confidence INTEGER DEFAULT 0;",
        "ALTER TABLE recruiters ADD COLUMN email_source VARCHAR(100);",
        "ALTER TABLE recruiters ADD COLUMN email_pattern_id INTEGER REFERENCES company_email_patterns(id) ON DELETE SET NULL;",
        "ALTER TABLE recruiters ADD COLUMN email_generated BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE recruiters ADD COLUMN email_verified_at TIMESTAMP;",
        "ALTER TABLE recruiters ADD COLUMN email_last_checked_at TIMESTAMP;",
        "ALTER TABLE recruiters ADD COLUMN canonical_company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL;",
        "ALTER TABLE recruiters ADD COLUMN historical_company_id INTEGER REFERENCES companies(company_id) ON DELETE SET NULL;",
        "ALTER TABLE recruiters ADD COLUMN company_domain_id INTEGER;",
        "ALTER TABLE recruiters ADD COLUMN raw_email_value VARCHAR(255);",
        "ALTER TABLE recruiters ADD COLUMN repair_reason TEXT;"
    ]

    for q in queries:
        try:
            c.execute(q)
        except Exception as e:
            print(f"Error executing table creation: {e}")
            
    for q in alter_queries:
        try:
            c.execute(q)
        except Exception as e:
            # Ignore duplicate column errors
            pass

    conn.commit()
    conn.close()
    print("Schema patched!")

if __name__ == '__main__':
    main()
