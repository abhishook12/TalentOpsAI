import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv("backend/.env")
load_dotenv(".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qpetzpxmuofuepvrqedk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_SECRET_KEY or SUPABASE_KEY in environment or .env file")

print(f"Connecting to Supabase Storage at {SUPABASE_URL}...")
client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket_name = "data-assets"

files_to_upload = [
    (r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScoutSetup.exe", "TalentOpsScoutSetup.exe", "application/vnd.microsoft.portable-executable"),
    (r"c:\TalentOpsAI\scout_desktop\dist\TalentOpsScoutSetup.zip", "TalentOpsScoutSetup.zip", "application/zip")
]

for local_path, dest_name, content_type in files_to_upload:
    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"Uploading {dest_name} ({size_mb:.2f} MB)...")
    t0 = time.time()
    with open(local_path, "rb") as f:
        res = client.storage.from_(bucket_name).upload(
            file=f,
            path=dest_name,
            file_options={"content-type": content_type, "upsert": "true"}
        )
    elapsed = round(time.time() - t0, 2)
    print(f"Uploaded {dest_name} in {elapsed}s: {res}")

print("All files uploaded to Supabase Storage data-assets successfully!")
