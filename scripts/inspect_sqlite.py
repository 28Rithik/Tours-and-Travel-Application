import sqlite3

con = sqlite3.connect('db.sqlite3')
cur = con.cursor()
tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
row_counts = []
for t in tables:
    try:
        cnt = cur.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        row_counts.append((t, cnt))
    except Exception as e:
        pass

for t, cnt in sorted(row_counts, key=lambda x: x[1], reverse=True)[:20]:
    print(f"{t}: {cnt:,} rows")
