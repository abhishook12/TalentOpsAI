import sqlite3

def main():
    conn = sqlite3.connect('C:/TalentOpsAI/backend/local_dev.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM recruiters WHERE state = 'Unknown' OR state IS NULL")
    count_unknown = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM recruiters")
    count_total = cursor.fetchone()[0]
    
    print(f"Total recruiters: {count_total}")
    print(f"Unknown states: {count_unknown}")
    if count_total > 0:
        print(f"Percentage unknown: {(count_unknown / count_total) * 100:.2f}%")
    
    # Also get a sample of unknown state recruiters to see what we have
    cursor.execute("SELECT id, name, company, email, phone, location FROM recruiters WHERE state = 'Unknown' OR state IS NULL LIMIT 5")
    sample = cursor.fetchall()
    print("\nSample of unknowns:")
    for row in sample:
        print(row)
        
    conn.close()

if __name__ == '__main__':
    main()
