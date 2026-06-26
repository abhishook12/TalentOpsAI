#!/usr/bin/env python
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("SELECT location, count(*) FROM recruiters WHERE state IS NULL OR state = '' GROUP BY location ORDER BY count(*) DESC LIMIT 30;")).fetchall()
for r in res:
    print(f"{r[1]}: {repr(r[0])}")
db.close()
