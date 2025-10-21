from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import sqlite3
import pandas as pd
import io
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev')

DB_PATH = os.environ.get('DV_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'dv_petitions.db'))

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def list_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r['name'] for r in cur.fetchall()]
    conn.close()
    return tables

@app.route('/', methods=['GET', 'POST'])
def index():
    tables = list_tables()
    table = request.values.get('table') or (tables[0] if tables else None)
    nrows = int(request.values.get('nrows', 100))
    where = request.values.get('where', '').strip()

    preview_df = None
    sql_preview = ''
    if table:
        where_clause = f" WHERE {where}" if where else ''
        sql_preview = f"SELECT * FROM {table}{where_clause} LIMIT {nrows}"
        try:
            conn = get_conn()
            preview_df = pd.read_sql_query(sql_preview, conn)
            conn.close()
        except Exception as e:
            flash(f'Preview query error: {e}', 'danger')
            preview_df = None

    return render_template('index.html', tables=tables, table=table, preview=preview_df, nrows=nrows, where=where)

@app.route('/sql', methods=['POST'])
def run_sql():
    query = request.form.get('sql', '').strip()
    if not query:
        flash('Empty query', 'warning')
        return redirect(url_for('index'))
    # Very basic safety: allow only SELECT
    if not query.lower().lstrip().startswith('select'):
        flash('Only SELECT queries are allowed via the SQL console for safety.', 'danger')
        return redirect(url_for('index'))
    try:
        conn = get_conn()
        df = pd.read_sql_query(query, conn)
        conn.close()
        html = df.to_html(classes='table table-striped', index=False)
        return render_template('sql.html', query=query, table_html=html)
    except Exception as e:
        flash(f'SQL error: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/download')
def download_preview():
    table = request.values.get('table')
    nrows = int(request.values.get('nrows', 100))
    where = request.values.get('where', '').strip()
    if not table:
        flash('No table selected', 'warning')
        return redirect(url_for('index'))
    where_clause = f" WHERE {where}" if where else ''
    sql = f"SELECT * FROM {table}{where_clause} LIMIT {nrows}"
    conn = get_conn()
    df = pd.read_sql_query(sql, conn)
    conn.close()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode('utf-8')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f'{table}_preview.csv')

@app.route('/plot', methods=['GET'])
def plot():
    table = request.values.get('table')
    column = request.values.get('column')
    topn = int(request.values.get('topn') or 20)
    tables = list_tables()
    if not table:
        return render_template('plot.html', tables=tables, labels=[], values=[], table=None, column=None)
    if not column:
        # get cols
        conn = get_conn()
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 1", conn)
        conn.close()
        cols = df.columns.tolist()
        return render_template('plot.html', tables=tables, cols=cols, labels=[], values=[], table=table, column=None)
    # compute counts
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT {column} FROM {table}", conn)
    conn.close()
    counts = df[column].fillna('NULL').astype(str).value_counts().head(topn)
    labels = counts.index.tolist()
    values = counts.values.tolist()
    cols = df.columns.tolist()
    return render_template('plot.html', tables=tables, cols=cols, labels=labels, values=values, table=table, column=column)

@app.route('/health')
def health():
    try:
        conn = get_conn()
        conn.execute('SELECT 1')
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
