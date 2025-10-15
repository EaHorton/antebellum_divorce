import sqlite3

DB_PATH = 'dv_petitions.db'

query = """
SELECT
  p.state,
  SUM(CASE WHEN LOWER(p.result) LIKE '%granted%' THEN 1 ELSE 0 END) AS granted_count,
  SUM(CASE WHEN LOWER(p.result) LIKE '%rejected%' OR LOWER(p.result) LIKE '%denied%' THEN 1 ELSE 0 END) AS rejected_count,
  COUNT(*) AS total_petitions
FROM Petitions p
GROUP BY p.state
ORDER BY p.state;
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    # print header
    print(f"{'state':<10} {'granted':>8} {'rejected':>9} {'total':>8}")
    for state, granted, rejected, total in rows:
        print(f"{state or '':<10} {granted:8d} {rejected:9d} {total:8d}")

if __name__ == "__main__":
    main()
# filepath: /Users/eahorton/hist8510/hist8550/queries/queries8.py
import sqlite3

DB_PATH = 'dv_petitions.db'

query = """
SELECT
  p.state,
  SUM(CASE WHEN LOWER(p.result) LIKE '%granted%' THEN 1 ELSE 0 END) AS granted_count,
  SUM(CASE WHEN LOWER(p.result) LIKE '%rejected%' OR LOWER(p.result) LIKE '%denied%' THEN 1 ELSE 0 END) AS rejected_count,
  COUNT(*) AS total_petitions
FROM Petitions p
GROUP BY p.state
ORDER BY p.state;
"""

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    # print header
    print(f"{'state':<10} {'granted':>8} {'rejected':>9} {'total':>8}")
    for state, granted, rejected, total in rows:
        print(f"{state or '':<10} {granted:8d} {rejected:9d} {total:8d}")

if __name__ == "__main__":
    main()