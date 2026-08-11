import os
from supabase import create_client, Client

from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://qpetzpxmuofuepvrqedk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    bucket_name = "data-assets"
    
    file_path = "C:/TalentOpsAI/backend/data/recruiters_full.parquet"
    destination_path = "recruiters_full.parquet"

    print(f"Uploading {file_path} (33MB) to bucket '{bucket_name}'...")
    with open(file_path, 'rb') as f:
        res = supabase.storage.from_(bucket_name).upload(
            file=f,
            path=destination_path,
            file_options={"content-type": "application/vnd.apache.parquet", "upsert": "true"}
        )
    print("Success!", res)
except Exception as e:
    print("Error:", e)
