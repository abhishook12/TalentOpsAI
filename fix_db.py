import sqlite3
import sys

def main():
    conn = sqlite3.connect('dev.db')
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE company_aliases ADD COLUMN canonical_company_id INTEGER;")
        print("Column canonical_company_id added successfully.")
    except Exception as e:
        print("Error:", e)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
