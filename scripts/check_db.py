import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import sqlite3
import pymysql
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

print("=== 1. Checking SQLite Fallback Database (receipt_bot.db) ===")
sqlite_path = BASE_DIR / "receipt_bot.db"
if sqlite_path.exists():
    conn = sqlite3.connect(sqlite_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("SQLite Tables:", tables)
    for t in tables:
        tname = t[0]
        c.execute(f"SELECT COUNT(*) FROM `{tname}`")
        cnt = c.fetchone()[0]
        print(f"  Table '{tname}': {cnt} rows")
        if cnt > 0:
            c.execute(f"SELECT * FROM `{tname}` LIMIT 3")
            rows = c.fetchall()
            print(f"    Sample data: {rows}")
    conn.close()
else:
    print("receipt_bot.db does not exist yet.")

print("\n=== 2. Testing MariaDB Server Connection ===")
try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3
    )
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES;")
    dbs = [d[0] for d in cursor.fetchall()]
    print("MariaDB Server Connection SUCCESSFUL!")
    print("Databases on MariaDB Server:", dbs)

    if DB_NAME in dbs:
        conn.select_db(DB_NAME)
        cursor.execute("SHOW TABLES;")
        m_tables = [t[0] for t in cursor.fetchall()]
        print(f"Tables in MariaDB '{DB_NAME}':", m_tables)
        for mt in m_tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{mt}`")
            cnt = cursor.fetchone()[0]
            print(f"  Table '{mt}': {cnt} rows")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"MariaDB Connection Failed: {type(e).__name__}: {e}")
