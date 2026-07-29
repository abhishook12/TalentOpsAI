import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("UPDATE recruiters SET state = NULL WHERE state = 'US'"))
db.commit()
print(f"Reverted {res.rowcount} 'US' states back to NULL.")
db.close()
