import os
from supabase import create_client, Client

SUPABASE_URL = "https://dcqvsvgrdsrgnbwwssup.supabase.co"
SUPABASE_KEY = "sb_publishable_3jrPOQs3sT_piWv8cnRlUQ_aa_ge1YS"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    bucket_name = "data-assets"
    
    # Try to create bucket if it doesn't exist (fails silently if we lack permissions, but we can check list)
    try:
        supabase.storage.create_bucket(bucket_name, public=True)
    except Exception:
        pass
        
    print("Testing upload...")
    res = supabase.storage.from_(bucket_name).upload(
        file=b"test data",
        path="test.txt",
        file_options={"upsert": "true"}
    )
    print("Success!", res)
except Exception as e:
    print("Error:", e)
