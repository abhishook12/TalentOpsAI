import sqlite3
import time
import requests

def run():
    try:
        conn = sqlite3.connect(r'C:\TalentOpsAI\backend\dev.db')
        c = conn.cursor()
        # Find user table
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in c.fetchall()]
        print("Tables:", tables)

        c.execute('SELECT * FROM api_keys LIMIT 1')
        keys = c.fetchall()
        print("Keys:", keys)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    run()
