import sqlite3
conn = sqlite3.connect('dev.db')
print(conn.execute("SELECT sql FROM sqlite_master WHERE type='table'").fetchall())
