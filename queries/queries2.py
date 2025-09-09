"""

This script answers the question: Which state granted the most petitions?
If you want to see results that include "granted" in some capacity, modift 
FROM Petitions p
GROUP BY p.state, p.year
ORDER BY p.state, p.year, petition_count DESC
to read 
FROM Petitions p
WHERE p.result LIKE '%granted%'
GROUP BY p.state, p.year
ORDER BY p.state, p.year, petition_count DESC
"""

import sqlite3
import pandas as pd

db_path = 'database.db'

query = '''
SELECT 
    p.state,
    p.result,
    COUNT(*) as petition_count
FROM Petitions p
WHERE p.result = 'granted'
GROUP BY p.state
ORDER BY p.state, petition_count DESC
'''




conn = sqlite3.connect('dv_petitions.db')
df = pd.read_sql_query(query, conn)
conn.close()

# Find most common reasoning per state and year 
most_common = df.sort_values(['state', 'petition_count'], ascending=[True, False])
top_petitions = most_common.groupby(['state']).first().reset_index()
for _, row in top_petitions.iterrows():

    print(f"State: {row['state']} ({row['petition_count']} cases)")