import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('C:/TalentOpsAI/backend/.env')

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing Supabase credentials")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket_name = "recruiter-data"

file_path = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
destination_path = "recruiters_full.parquet"

print(f"Uploading {file_path} to bucket '{bucket_name}' at '{destination_path}'...")

try:
    with open(file_path, 'rb') as f:
        res = supabase.storage.from_(bucket_name).upload(
            file=f,
            path=destination_path,
            file_options={"content-type": "application/vnd.apache.parquet", "upsert": "true"}
        )
    print("Upload successful!")
except Exception as e:
    print(f"Failed to upload: {e}")
