from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, Response
import io
import csv
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
    page = int(request.values.get('page', 1))

    preview_df = None
    sql_preview = ''
    if table:
        where_clause = f" WHERE {where}" if where else ''
        # Get total count for pagination
        try:
            conn = get_conn()
            total_count = conn.execute(f"SELECT COUNT(*) FROM {table} {where_clause}").fetchone()[0]
            offset = (page - 1) * nrows
            sql_preview = f"SELECT * FROM {table}{where_clause} LIMIT {nrows} OFFSET {offset}"
            preview_df = pd.read_sql_query(sql_preview, conn)
            conn.close()
        except Exception as e:
            flash(f'Preview query error: {e}', 'danger')
            preview_df = None
            total_count = 0

    total_pages = max(1, (total_count + nrows - 1) // nrows if table else 1)
    return render_template('index.html', tables=tables, table=table, preview=preview_df, nrows=nrows, where=where, page=page, total_pages=total_pages, total_count=total_count)

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


@app.route('/prebuilt', methods=['GET'])
def prebuilt():
    """Run one of a few safe, read-only prebuilt queries and show results."""
    q = request.values.get('q')
    queries = {
        'reasoning_by_state': {
            'label': 'Most common reasoning by state (top 1)',
            'sql': """
SELECT state, reasoning, cnt FROM (
  SELECT p.state, r.reasoning, COUNT(*) as cnt,
    ROW_NUMBER() OVER (PARTITION BY p.state ORDER BY COUNT(*) DESC) rn
  FROM Petitions p
  JOIN Petition_Reasoning_Lookup pr ON p.petition_id = pr.petition_id
  JOIN Reasoning r ON pr.reasoning_id = r.reasoning_id
  GROUP BY p.state, r.reasoning
) WHERE rn = 1 ORDER BY state
"""
        },
        'counts_by_result': {
            'label': 'Counts by state and result',
            'sql': "SELECT p.state, r.result, COUNT(*) as cnt FROM Petitions p JOIN Result r ON p.petition_id=r.petition_id GROUP BY p.state, r.result ORDER BY p.state, cnt DESC"
        }
    }
    if q not in queries:
        flash('Unknown prebuilt query', 'warning')
        return redirect(url_for('index'))
    sql = queries[q]['sql']
    try:
        conn = get_conn()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        html = df.to_html(classes='table table-striped', index=False)
        return render_template('sql.html', query=queries[q]['label'], table_html=html)
    except Exception as e:
        flash(f'Prebuilt query error: {e}', 'danger')
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
    chart_type = request.values.get('chart_type') or 'bar'
    group_by = request.values.get('group_by') or ''
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
    # optionally group by another column
    if group_by:
        df = pd.read_sql_query(f"SELECT {column}, {group_by} FROM {table}", conn)
    else:
        df = pd.read_sql_query(f"SELECT {column} FROM {table}", conn)
    conn.close()
    if group_by:
        # produce grouped labels like "group:value"
        df[column] = df[column].fillna('NULL').astype(str)
        df[group_by] = df[group_by].fillna('NULL').astype(str)
        grp = df.groupby([group_by, column]).size().reset_index(name='cnt')
        grp['label'] = grp[group_by].astype(str) + ':' + grp[column].astype(str)
        top = grp.sort_values('cnt', ascending=False).head(topn)
        labels = top['label'].tolist()
        values = top['cnt'].tolist()
    else:
        counts = df[column].fillna('NULL').astype(str).value_counts().head(topn)
        labels = counts.index.tolist()
        values = counts.values.tolist()
    cols = df.columns.tolist()
    return render_template('plot.html', tables=tables, cols=cols, labels=labels, values=values, table=table, column=column, chart_type=chart_type, group_by=group_by)


@app.route('/plot_data')
def plot_data():
    """Return JSON with labels and values for the requested plot parameters."""
    table = request.values.get('table')
    column = request.values.get('column')
    topn = int(request.values.get('topn') or 20)
    group_by = request.values.get('group_by') or ''
    if not table or not column:
        return jsonify({'error': 'table and column required'}), 400
    conn = get_conn()
    try:
        if group_by:
            df = pd.read_sql_query(f"SELECT {column}, {group_by} FROM {table}", conn)
            df[column] = df[column].fillna('NULL').astype(str)
            df[group_by] = df[group_by].fillna('NULL').astype(str)
            grp = df.groupby([group_by, column]).size().reset_index(name='cnt')
            grp['label'] = grp[group_by].astype(str) + ':' + grp[column].astype(str)
            top = grp.sort_values('cnt', ascending=False).head(topn)
            labels = top['label'].tolist()
            values = top['cnt'].tolist()
        else:
            df = pd.read_sql_query(f"SELECT {column} FROM {table}", conn)
            counts = df[column].fillna('NULL').astype(str).value_counts().head(topn)
            labels = counts.index.tolist()
            values = counts.values.tolist()
        return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/plot_data.csv')
def plot_data_csv():
    """Return CSV for the same parameters as /plot_data."""
    resp = plot_data()
    if resp[1] != 200 if isinstance(resp, tuple) else False:
        # plot_data returned an error
        return resp
    data = resp.get_json() if hasattr(resp, 'get_json') else (resp[0] if isinstance(resp, tuple) else {})
    labels = data.get('labels', [])
    values = data.get('values', [])
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['label', 'value'])
    for l, v in zip(labels, values):
        writer.writerow([l, v])
    return Response(out.getvalue(), mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=plot_data.csv"})

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
