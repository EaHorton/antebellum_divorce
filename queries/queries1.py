"""

This script answers the question: What were the most common courts in each state? 


"""

import sqlite3
import pandas as pd

db_path = 'database.db'

query = '''
SELECT 
    c.state,
    c.court,
    COUNT(*) as court_count
FROM Court c
GROUP BY c.state, c.court
ORDER BY c.state, court_count DESC
'''

conn = sqlite3.connect('dv_petitions.db')
df = pd.read_sql_query(query, conn)
conn.close()

# Find most common courts per state
most_common = df.sort_values(['state', 'court'], ascending=[True, False])
top3_courts = most_common.groupby('state').head(3)
for state in top3_courts['state'].unique():
    print(f"\n{state}:")
    subset = top3_courts[top3_courts['state'] == state]
    for _, row in subset.iterrows():
        print(f"  {row['court']} ({row['court_count']} cases)")