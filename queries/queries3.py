"""

This script answers the question: How did accusations change over time?
Not super relevant because I don't have statistical significance. 

"""

import sqlite3
import pandas as pd

db_path = 'database.db'

query = '''
SELECT 
    p.state,
    r.reasoning,
    p.year,
    COUNT(*) as reasoning_count
FROM Reasoning r
JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
JOIN Petitions p ON prl.petition_id = p.petition_id
GROUP BY p.state, r.reasoning, p.year
ORDER BY p.state, p.year, reasoning_count DESC
'''

conn = sqlite3.connect('dv_petitions.db')
df = pd.read_sql_query(query, conn)
conn.close()

# Find most common reasoning per state and year 
most_common = df.sort_values(['state', 'reasoning_count'], ascending=[True, False])
top_reasoning = most_common.groupby(['state', 'year']).first().reset_index()
for _, row in top_reasoning.iterrows():
    print(f"State: {row['state']}, Reasoning: {row['reasoning']}, Year: {row['year']} ({row['reasoning_count']} cases)")