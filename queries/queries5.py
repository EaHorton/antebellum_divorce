"""

This script answers the question: How often did each state see interracial sex as a reasoning? 


"""

import sqlite3
import pandas as pd

db_path = 'database.db'

query = '''
SELECT 
    p.state,
    r.reasoning,
    COUNT(*) as petition_count
FROM Reasoning r
JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
JOIN Petitions p ON prl.petition_id = p.petition_id
WHERE r.reasoning IN ('interracial_sex(M)', 'interracial_sex(F)')
GROUP BY p.state, r.reasoning
'''




conn = sqlite3.connect('dv_petitions.db')
df = pd.read_sql_query(query, conn)
conn.close()

# How many instances of interracial sex in each state 
interracial_sex = df.sort_values(['state', 'petition_count'], ascending=[True, False])
top_petitions = interracial_sex.groupby(['state']).first().reset_index()
for _, row in top_petitions.iterrows():

    print(f"State: {row['state']} ({row['petition_count']} cases)")