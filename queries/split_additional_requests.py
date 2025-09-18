import sqlite3

DB_PATH = 'dv_petitions.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Read all additional requests and their IDs
c.execute('SELECT additional_requests_id, additional_requests FROM Additional_Requests')
rows = c.fetchall()

# Prepare new rows: split requests by comma, keep same ID for each
split_rows = []
for addreq_id, addreq in rows:
    if addreq:
        requests = [r.strip() for r in addreq.split(',') if r.strip()]
        for req in requests:
            split_rows.append((addreq_id, req))

# Create new table for split requests
c.execute('''DROP TABLE IF EXISTS Additional_Requests_Split''')
c.execute('''CREATE TABLE Additional_Requests_Split (
    additional_requests_id INTEGER,
    additional_request TEXT
)''')
c.executemany('INSERT INTO Additional_Requests_Split VALUES (?, ?)', split_rows)

conn.commit()
conn.close()
print('Additional_Requests_Split table created and populated.')
