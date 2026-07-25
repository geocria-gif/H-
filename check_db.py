import sqlite3
conn = sqlite3.connect(r'C:\Users\frj_c\OneDrive\CPR-CN\SISPM\hextra_2026-07-14 (1).sqlite')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
for t in tables:
    print(f'=== {t[0]} ===')
    cursor.execute(f'SELECT sql FROM sqlite_master WHERE type="table" AND name="{t[0]}"')
    result = cursor.fetchone()
    if result:
        print(result[0])
    print()