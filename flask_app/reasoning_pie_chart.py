"""
Pie Chart Visualization for Divorce Reasons
Based on queries4.py data - Shows distribution of divorce reasons across all states

This script creates a pie chart similar to the Plotly template example.
It groups smaller reasons into "Other" category for better visualization.
"""

import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Database path
db_path = '../dv_petitions.db.bak'

# Query to get all reasoning counts across all states
query = '''
SELECT 
    r.reasoning,
    COUNT(*) as reasoning_count
FROM Reasoning r
JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
JOIN Petitions p ON prl.petition_id = p.petition_id
GROUP BY r.reasoning
ORDER BY reasoning_count DESC
'''

# Connect and fetch data
conn = sqlite3.connect(db_path)
df = pd.read_sql_query(query, conn)
conn.close()

# Group smaller reasons into "Other" category (similar to the template example)
# Reasons with less than 3% of total will be grouped as "Other"
threshold = df['reasoning_count'].sum() * 0.03
df.loc[df['reasoning_count'] < threshold, 'reasoning'] = 'Other reasons'

# Aggregate after grouping
df = df.groupby('reasoning')['reasoning_count'].sum().reset_index()
df = df.sort_values('reasoning_count', ascending=False)

print("\n=== Divorce Reasons Distribution ===")
print(df.to_string(index=False))
print(f"\nTotal cases: {df['reasoning_count'].sum()}")

# Create pull array - highlight the most common reason by pulling it out
pull_values = [0.2] + [0] * (len(df) - 1)

# Create pie chart using graph_objects for pull effect (following the template structure)
fig = go.Figure(data=[go.Pie(
    labels=df['reasoning'].tolist(),
    values=df['reasoning_count'].tolist(),
    pull=pull_values  # Pull out the top reason
)])

# Update layout for better appearance
fig.update_traces(textposition='inside', textinfo='percent+label')
fig.update_layout(
    title='Distribution of Divorce Reasons in Antebellum America',
    height=700,
    showlegend=True,
    legend=dict(
        orientation="v",
        yanchor="middle",
        y=0.5,
        xanchor="left",
        x=1.02
    )
)

# Show the interactive chart
fig.show()

print("\n✨ Pie chart visualization opened in your browser!")
