"""

This script answers the question: What were the top 3 reasonings cited for divorce 
in each state where the husband is the party accused?


"""

import sqlite3
import pandas as pd

db_path = 'dv_petitions.db'

query = '''
SELECT 
    p.state,
    r.reasoning,
    COUNT(*) as reasoning_count
FROM Reasoning r
JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
JOIN Petitions p ON prl.petition_id = p.petition_id
WHERE r.party_accused = 'husband_accused'
GROUP BY p.state, r.reasoning
ORDER BY p.state, reasoning_count DESC
'''

conn = sqlite3.connect(db_path)
df = pd.read_sql_query(query, conn)
conn.close()

# Find top 3 reasonings per state where husband is accused
top3_reasonings = df.groupby('state').head(3)

print("Top 3 Reasonings Where Husband is Accused (by State):")
print("=" * 60)

for state in top3_reasonings['state'].unique():
    print(f"\n{state}:")
    subset = top3_reasonings[top3_reasonings['state'] == state]
    for _, row in subset.iterrows():
        print(f"  {row['reasoning']} ({row['reasoning_count']} cases)")
