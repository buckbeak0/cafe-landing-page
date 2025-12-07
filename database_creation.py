import sqlite3

db = sqlite3.connect("data/cafe.db")
cur = db.cursor()

cur.execute("""CREATE TABLE reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    table_no INTEGER,
    res_time TEXT,
    pno INTEGER,
    email TEXT
)""")

db.commit()