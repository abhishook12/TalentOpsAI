import os
from sqlalchemy import text
from app.database import engine

def run():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN email_pattern VARCHAR(150);"))
        except Exception as e: print("Already has email_pattern:", e)
        
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN notes TEXT;"))
        except Exception as e: print("Already has notes:", e)
        
        try:
            conn.execute(text("ALTER TABLE companies ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
        except Exception as e: print("Already has is_active:", e)

if __name__ == "__main__":
    run()
