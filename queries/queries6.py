"""

This script answers the question: Of those petitons that were granted in each state, what was most common reasons cited?

"""

import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('dv_petitions.db')

# SQL query: Get state, reasoning, and count for granted petitions
query = '''
SELECT 
    p.state,
    r.reasoning,
    COUNT(*) as reasoning_count
FROM Petitions p
JOIN Petition_Reasoning_Lookup prl ON p.petition_id = prl.petition_id
JOIN Reasoning r ON prl.reasoning_id = r.reasoning_id
WHERE p.result = 'granted'
GROUP BY p.state, r.reasoning
ORDER BY p.state, reasoning_count DESC
'''

df = pd.read_sql_query(query, conn)

# Find the most frequent reasoning for each state
most_common = df.sort_values(['state', 'reasoning_count'], ascending=[True, False])
top_reasoning = most_common.groupby('state').first().reset_index()

# Print results
for _, row in top_reasoning.iterrows():
    print(f"{row['state']}: {row['reasoning']} ({row['reasoning_count']} cases)")

conn.close()