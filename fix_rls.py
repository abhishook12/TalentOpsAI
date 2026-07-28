import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def main():
    load_dotenv("C:\\TalentOpsAI\\backend\\.env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found!")
        return

    print("Connecting to database to fix RLS...")
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Get all tables in the public schema
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';"))
        tables = [row[0] for row in result]
        
        for table in tables:
            print(f"Enabling Row Level Security (RLS) for table: {table}")
            conn.execute(text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"))
            
        conn.commit()
        
    print("\nSUCCESS! RLS has been enabled on all public tables.")
    print("The Supabase Advisor warnings should now be completely cleared!")

if __name__ == "__main__":
    main()
