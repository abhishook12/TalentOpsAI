import asyncio
import sqlalchemy
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv("C:/TalentOpsAI/backend/.env")
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

password = "Kx7!mQp2"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

with engine.connect() as conn:
    conn.execute(text(f"UPDATE users SET password_hash = '{hashed}', status = 'Active' WHERE email = 'abhishekjadon706@gmail.com'"))
    conn.commit()
    print("Password updated successfully.")
