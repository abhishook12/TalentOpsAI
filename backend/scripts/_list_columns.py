import os, psycopg
from dotenv import load_dotenv
load_dotenv('.env')
u = os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')
c = psycopg.connect(u).cursor()
print("=== RECRUITERS COLUMNS ===")
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='recruiters' ORDER BY ordinal_position")
for r in c.fetchall():
    print(r[0])
print("\n=== COMPANIES COLUMNS ===")
c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='companies' ORDER BY ordinal_position")
for r in c.fetchall():
    print(r[0])
