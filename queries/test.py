import sqlite3
conn = sqlite3.connect('dv_petitions.db')
c = conn.cursor()
c.execute('SELECT * FROM Result LIMIT 5')
print(c.fetchall())
conn.close()