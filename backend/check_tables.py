import sqlite3
import os
print(os.path.abspath('dev.db'))
c = sqlite3.connect('dev.db').cursor()
print([r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()])
