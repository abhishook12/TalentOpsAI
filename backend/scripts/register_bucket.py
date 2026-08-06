import os
import uuid
import psycopg
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')
DB_URL = os.getenv('DATABASE_URL').replace('postgresql+psycopg://', 'postgresql://')

conn = psycopg.connect(DB_URL, autocommit=True)
cur = conn.cursor()

file_path = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
if not os.path.exists(file_path):
    print("File not found")
    exit(1)

file_size_bytes = os.path.getsize(file_path)
path_name = f"archives/recruiters_full_{uuid.uuid4().hex[:8]}.parquet"
metadata = f'{{"size": {file_size_bytes}, "mimetype": "application/vnd.apache.parquet"}}'

print(f"Registering {file_path} in storage.objects as {path_name}...")
cur.execute("""
    INSERT INTO storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version)
    VALUES (%s, 'recruiter-data', %s, NULL, NOW(), NOW(), NOW(), %s, %s)
""", (str(uuid.uuid4()), path_name, metadata, str(uuid.uuid4())))

print("Successfully registered in bucket metadata!")
conn.close()
