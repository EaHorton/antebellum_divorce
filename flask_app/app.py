from flask import Flask, render_template, jsonify
import sqlite3
import plotly
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import json

app = Flask(__name__)

# Database path
DB_PATH = '../dv_petitions.db.bak'

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Main page with dashboard"""
    return render_template('index.html')

@app.route('/reasoning')
def reasoning():
    """Reasoning analysis page with state selector"""
    return render_template('reasoning.html')

@app.route('/api/stats')
def get_stats():
    """Get basic statistics"""
    conn = get_db_connection()
    
    # Total petitions
    total = conn.execute('SELECT COUNT(*) as count FROM Petitions').fetchone()['count']
    
    # Petitions by state
    by_state = conn.execute('''
        SELECT state, COUNT(*) as count 
        FROM Petitions 
        GROUP BY state
        ORDER BY count DESC
    ''').fetchall()
    
    # Petitions by year
    by_year = conn.execute('''
        SELECT year, COUNT(*) as count 
        FROM Petitions 
        WHERE year IS NOT NULL AND year != ''
        GROUP BY year
        ORDER BY year
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'total': total,
        'by_state': [dict(row) for row in by_state],
        'by_year': [dict(row) for row in by_year]
    })

@app.route('/plot/petitions_by_state')
def plot_petitions_by_state():
    """Generate a bar chart of petitions by state"""
    conn = get_db_connection()
    
    df = pd.read_sql_query('''
        SELECT state, COUNT(*) as count 
        FROM Petitions 
        WHERE state IS NOT NULL AND state != ''
        GROUP BY state
        ORDER BY count DESC
    ''', conn)
    
    conn.close()
    
    fig = px.bar(df, x='state', y='count', 
                 title='Divorce Petitions by State',
                 labels={'state': 'State', 'count': 'Number of Petitions'},
                 color='count',
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        template='plotly_white'
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/plot/petitions_by_year')
def plot_petitions_by_year():
    """Generate a line chart of petitions over time"""
    conn = get_db_connection()
    
    df = pd.read_sql_query('''
        SELECT year, COUNT(*) as count 
        FROM Petitions 
        WHERE year IS NOT NULL AND year != ''
        GROUP BY year
        ORDER BY year
    ''', conn)
    
    conn.close()
    
    fig = px.line(df, x='year', y='count', 
                  title='Divorce Petitions Over Time',
                  labels={'year': 'Year', 'count': 'Number of Petitions'},
                  markers=True)
    
    fig.update_layout(
        height=500,
        template='plotly_white'
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/plot/petitions_by_result')
def plot_petitions_by_result():
    """Generate a pie chart of petition results"""
    conn = get_db_connection()
    
    df = pd.read_sql_query('''
        SELECT result, COUNT(*) as count 
        FROM Petitions 
        WHERE result IS NOT NULL AND result != ''
        GROUP BY result
        ORDER BY count DESC
    ''', conn)
    
    conn.close()
    
    fig = px.pie(df, values='count', names='result', 
                 title='Petition Results Distribution',
                 hole=0.3)
    
    fig.update_layout(
        height=500,
        template='plotly_white'
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/plot/petitions_by_county')
def plot_petitions_by_county():
    """Generate a bar chart of top counties by petition count"""
    conn = get_db_connection()
    
    df = pd.read_sql_query('''
        SELECT county, state, COUNT(*) as count 
        FROM Petitions 
        WHERE county IS NOT NULL AND county != ''
        GROUP BY county, state
        ORDER BY count DESC
        LIMIT 20
    ''', conn)
    
    conn.close()
    
    # Combine county and state for better labels
    df['location'] = df['county'] + ', ' + df['state']
    
    fig = px.bar(df, x='location', y='count', 
                 title='Top 20 Counties by Petition Count',
                 labels={'location': 'County, State', 'count': 'Number of Petitions'},
                 color='count',
                 color_continuous_scale='Viridis')
    
    fig.update_layout(
        xaxis_tickangle=-45,
        height=600,
        template='plotly_white'
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/data/petitions')
def get_petitions():
    """Get all petitions data"""
    conn = get_db_connection()
    petitions = conn.execute('SELECT * FROM Petitions LIMIT 100').fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in petitions])

@app.route('/plot/reasoning_by_state/<state>')
def plot_reasoning_by_state(state):
    """Generate a pie chart of top 3 reasoning for a specific state"""
    conn = get_db_connection()
    
    query = '''
    SELECT 
        r.reasoning,
        COUNT(*) as reasoning_count
    FROM Reasoning r
    JOIN Petition_Reasoning_Lookup prl ON r.reasoning_id = prl.reasoning_id
    JOIN Petitions p ON prl.petition_id = p.petition_id
    WHERE p.state = ?
    GROUP BY r.reasoning
    ORDER BY reasoning_count DESC
    LIMIT 3
    '''
    
    df = pd.read_sql_query(query, conn, params=(state,))
    conn.close()
    
    if df.empty:
        # Return empty chart if no data
        fig = px.pie(values=[1], names=['No Data'], title=f'Top 3 Divorce Reasons in {state}')
    else:
        # Create pull array - pull out the top reason (first slice)
        pull_values = [0.2] + [0] * (len(df) - 1)
        
        fig = go.Figure(data=[go.Pie(
            labels=df['reasoning'].tolist(),
            values=df['reasoning_count'].tolist(),
            pull=pull_values
        )])
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(title=f'Top 3 Divorce Reasons in {state}')
        fig.update_layout(
            height=500,
            template='plotly_white',
            showlegend=True
        )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

@app.route('/plot/reasoning_all_states')
def plot_reasoning_all_states():
    """Generate a pie chart showing all reasoning across all states"""
    conn = get_db_connection()
    
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
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Group smaller reasons into "Other" category
    # Keep top reasons, combine rest as "Other"
    threshold = df['reasoning_count'].sum() * 0.03  # Less than 3% goes to "Other"
    df.loc[df['reasoning_count'] < threshold, 'reasoning'] = 'Other reasons'
    
    # Aggregate after grouping
    df = df.groupby('reasoning')['reasoning_count'].sum().reset_index()
    df = df.sort_values('reasoning_count', ascending=False)
    
    # Create pull array - pull out the top reason (most common)
    pull_values = [0.2] + [0] * (len(df) - 1)
    
    fig = go.Figure(data=[go.Pie(
        labels=df['reasoning'].tolist(),
        values=df['reasoning_count'].tolist(),
        pull=pull_values
    )])
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        title='Distribution of Divorce Reasons Across All States',
        height=600,
        template='plotly_white',
        showlegend=True
    )
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

if __name__ == '__main__':
    app.run(debug=True, port=5000)
