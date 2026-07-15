import asyncio
import sqlalchemy
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv("C:/TalentOpsAI/backend/.env")
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT email, status FROM users WHERE email = 'abhishekjadon706@gmail.com'"))
    row = result.fetchone()
    if row:
        print(f"User found: {row.email}, Status: {row.status}")
    else:
        print("User not found.")
