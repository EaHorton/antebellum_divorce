import sqlite3

DB_PATH = 'dv_petitions.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT year, COUNT(*) AS petition_count
        FROM Petitions
        GROUP BY year
    """)
    rows = cur.fetchall()
    conn.close()

    # Normalize year display and sort: numeric years first (asc), then non-numeric, then Unknown
    normalized = []
    for year, cnt in rows:
        if year is None or (isinstance(year, str) and year.strip() == ""):
            display = "Unknown"
        else:
            display = str(year).strip()
        normalized.append((display, cnt))

    def sort_key(item):
        y = item[0]
        if y == "Unknown":
            return (2, 0)
        try:
            return (0, int(y))
        except Exception:
            return (1, y.lower())

    normalized.sort(key=sort_key)

    print(f"{'year':<10} {'petitions':>10}")
    for year, cnt in normalized:
        print(f"{year:<10} {cnt:10d}")

if __name__ == "__main__":
    main()