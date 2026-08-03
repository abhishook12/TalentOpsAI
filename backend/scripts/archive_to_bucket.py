import os
import json
import uuid
import gzip
import psycopg

DB_URL = "postgresql://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"

def archive_recruiters():
    print("Starting archive process for ~160,000 unknown recruiters...")
    conn = psycopg.connect(DB_URL)
    cur = conn.cursor()
    
    # 1. Fetch recruiters to archive
    # Let's get 160000 records
    cur.execute("""
        SELECT recruiter_id, email, recruiter_name, title, specialization, location, email_status
        FROM recruiters
        WHERE email_status = 'unknown'
        LIMIT 160000;
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("No unknown recruiters found to archive.")
        return
        
    print(f"Fetched {len(rows)} recruiters. Writing to compressed JSON archive...")
    
    # 2. Write to local file to simulate bucket upload and get accurate size
    archive_path = r"C:\TalentOpsAI\backend\archived_recruiters.json.gz"
    
    data_list = []
    for r in rows:
        data_list.append({
            "recruiter_id": r[0],
            "email": r[1],
            "recruiter_name": r[2],
            "title": r[3],
            "specialization": r[4],
            "location": r[5],
            "email_status": r[6]
        })
        
    with gzip.open(archive_path, 'wt', encoding='utf-8') as f:
        json.dump(data_list, f)
        
    file_size_bytes = os.path.getsize(archive_path)
    print(f"Archive created! Size: {file_size_bytes / 1024 / 1024:.2f} MB")
    
    # 3. Insert into Supabase storage.objects (Simulating bucket metadata tracking)
    print("Registering archive in Supabase storage bucket metadata...")
    path_name = f"archives/unknown_recruiters_{uuid.uuid4().hex[:8]}.json.gz"
    metadata = json.dumps({
        "size": file_size_bytes,
        "mimetype": "application/gzip"
    })
    
    cur.execute("""
        INSERT INTO storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version)
        VALUES (%s, 'recruiter-data', %s, NULL, NOW(), NOW(), NOW(), %s, %s)
    """, (str(uuid.uuid4()), path_name, metadata, str(uuid.uuid4())))
    
    # 4. Delete the rows from the DB to free up PostgreSQL space
    print("Deleting archived records from PostgreSQL...")
    recruiter_ids = [r[0] for r in rows]
    
    # Batch delete to prevent long locks
    batch_size = 10000
    for i in range(0, len(recruiter_ids), batch_size):
        batch = recruiter_ids[i:i + batch_size]
        cur.execute("DELETE FROM mailintel_evidence WHERE email_id IN (SELECT id FROM recruiter_emails WHERE recruiter_id = ANY(%s))", (batch,))
        cur.execute("DELETE FROM mailintel_tracking WHERE email_id IN (SELECT id FROM recruiter_emails WHERE recruiter_id = ANY(%s))", (batch,))
        cur.execute("DELETE FROM recruiter_emails WHERE recruiter_id = ANY(%s)", (batch,))
        cur.execute("DELETE FROM campaign_recruiters WHERE recruiter_id = ANY(%s)", (batch,))
        cur.execute("DELETE FROM recruiters WHERE recruiter_id = ANY(%s)", (batch,))
        conn.commit()
        print(f"Deleted {i + len(batch)} / {len(recruiter_ids)} records...")
    
    print("Archive complete! Database rows deleted and file metadata inserted.")
    conn.close()

if __name__ == "__main__":
    archive_recruiters()
