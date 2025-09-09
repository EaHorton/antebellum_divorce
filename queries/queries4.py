"""

This script answers the question: What was the most common accusations (3) in each state? 


"""

import sqlite3
import pandas as pd

db_path = 'database.db'

query = '''
SELECT 
    p.state,
    r.reasoning,
    COUNT(*) as reasoning_count
FROM Reasoning r
JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
JOIN Petitions p ON prl.petition_id = p.petition_id
GROUP BY p.state, r.reasoning
ORDER BY p.state, reasoning_count DESC
'''

conn = sqlite3.connect('dv_petitions.db')
df = pd.read_sql_query(query, conn)
conn.close()

# Find most common reasoning per state
most_common = df.sort_values(['state', 'reasoning_count'], ascending=[True, False])
top3_reasonings = most_common.groupby('state').head(3)
for state in top3_reasonings['state'].unique():
    print(f"\n{state}:")
    subset = top3_reasonings[top3_reasonings['state'] == state]
    for _, row in subset.iterrows():
        print(f"  {row['reasoning']} ({row['reasoning_count']} cases)")
