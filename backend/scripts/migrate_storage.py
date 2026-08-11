import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('C:/TalentOpsAI/backend/.env')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# Use the SECRET key so we have permissions to create a bucket and set it to public
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    print("Missing Supabase credentials in .env")
    exit(1)

print(f"Connecting to {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

bucket_name = "data-assets"

try:
    print(f"Creating bucket '{bucket_name}'...")
    supabase.storage.create_bucket(bucket_name, name=bucket_name)
    print("Bucket created successfully!")
except Exception as e:
    print("Error creating bucket (may already exist):", e)
    try:
        supabase.storage.update_bucket(bucket_name, {"public": True})
        print("Bucket updated to public.")
    except Exception as e2:
        pass

file_path = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
destination_path = "recruiters_full.parquet"

print(f"Uploading {file_path} to '{bucket_name}'...")
with open(file_path, 'rb') as f:
    try:
        res = supabase.storage.from_(bucket_name).upload(
            file=f,
            path=destination_path,
            file_options={"content-type": "application/vnd.apache.parquet", "upsert": "true"}
        )
        print("Upload Success!")
    except Exception as e:
        print("Error uploading:", e)
