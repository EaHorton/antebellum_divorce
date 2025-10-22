from flask import Flask, render_template_string, request, send_file, jsonify
import pandas as pd
from .db_helper import list_tables, get_conn, compute_plot_data
import io, csv
import re

app = Flask(__name__)

INDEX_HTML = '''
<!doctype html>
<html>
<head><title>DV Petitions Web UI</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css">
</head>
<body class="p-3">
<div class="container">
  <h1>DV Petitions Web UI</h1>
  <form method="get" class="form-inline mb-3">
    <label class="mr-2">Table</label>
    <select name="table" class="form-control mr-2">
      {% for t in tables %}
      <option value="{{t}}" {% if t==table %}selected{% endif %}>{{t}}</option>
      {% endfor %}
    </select>
    <label class="mr-2">Rows</label>
    <input name="rows" value="{{rows}}" class="form-control mr-2" style="width:80px" />
    <label class="mr-2">Page</label>
    <input name="page" value="{{page}}" class="form-control mr-2" style="width:80px" />
    <button class="btn btn-primary">Preview</button>
  </form>

  {% if preview_html %}
  <div class="table-responsive">{{ preview_html|safe }}</div>
  {% endif %}
  <div class="mt-4">
    <a class="btn btn-secondary" href="/plot?table={{table}}">Visualize</a>
  </div>
</div>
</body>
</html>
'''


PLOT_HTML = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Plot</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<div class="container mt-3">
  <h1>Plot</h1>
  <div class="mb-2">
    <a href="/">Back</a>
  </div>
  <form id="plot-form" class="form-inline mb-3">
    <label class="mr-2">Table</label>
    <select id="table" name="table" class="form-control mr-2">
      {% for t in tables %}
      <option value="{{t}}" {% if t==table %}selected{% endif %}>{{t}}</option>
      {% endfor %}
    </select>
    <label class="mr-2">Column</label>
    <input id="column" name="column" value="{{column}}" class="form-control mr-2" />
    <label class="mr-2">Top N</label>
    <input id="topn" name="topn" value="{{topn}}" class="form-control mr-2" style="width:80px" />
    <button id="plot-btn" class="btn btn-primary">Plot</button>
  </form>

  <div>
    <canvas id="chart" width="800" height="400"></canvas>
  </div>
  <div class="mt-3">
    <a id="csv-link" class="btn btn-outline-secondary" href="#">Download CSV</a>
    <a id="json-link" class="btn btn-outline-secondary" href="#">Download JSON</a>
  </div>

  <script>
  async function fetchData(table, column, topn){
    const url = `/plot_data?table=${encodeURIComponent(table)}&column=${encodeURIComponent(column)}&topn=${encodeURIComponent(topn)}`;
    const r = await fetch(url);
    if(!r.ok) throw new Error('Fetch error');
    return r.json();
  }

  function renderChart(labels, values){
    const ctx = document.getElementById('chart').getContext('2d');
    if(window._chart) window._chart.destroy();
    window._chart = new Chart(ctx, {
      type: 'bar',
      data: { labels: labels, datasets: [{ label: 'Count', data: values, backgroundColor: 'rgba(54,162,235,0.6)' }] },
      options: { responsive: true, indexAxis: 'y' }
    });
  }

  document.getElementById('plot-form').addEventListener('submit', async function(e){
    e.preventDefault();
    const table = document.getElementById('table').value;
    const column = document.getElementById('column').value;
    const topn = document.getElementById('topn').value;
    try{
      const data = await fetchData(table, column, topn);
      renderChart(data.labels, data.values);
      document.getElementById('csv-link').href = `/plot_export?table=${encodeURIComponent(table)}&column=${encodeURIComponent(column)}&topn=${encodeURIComponent(topn)}`;
      document.getElementById('json-link').href = `/plot_data?table=${encodeURIComponent(table)}&column=${encodeURIComponent(column)}&topn=${encodeURIComponent(topn)}`;
    }catch(err){
      alert('Error fetching plot data: ' + err);
    }
  });

  // auto-run if column prefilled
  if(document.getElementById('column').value){
    document.getElementById('plot-btn').click();
  }
  </script>
</div>
</body>
</html>
'''


SQL_HTML = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8"><title>SQL Console</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css">
</head>
<body class="p-3">
<div class="container">
  <h1>SQL Console (read-only)</h1>
  <p class="text-muted">Only single SELECT statements allowed. A LIMIT will be added if missing.</p>
  <form method="post">
    <div class="mb-2">
      <textarea name="query" rows="6" class="form-control">{{query or ''}}</textarea>
    </div>
    <button class="btn btn-primary">Run</button>
    <a class="btn btn-secondary" href="/">Back</a>
  </form>
  <div class="mt-3">
    {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
    {% if table_html %}
      <div class="table-responsive">{{ table_html|safe }}</div>
    {% endif %}
  </div>
</div>
</body>
</html>
'''


JOIN_HTML = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8"><title>Join Builder</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.2/dist/css/bootstrap.min.css">
</head>
<body class="p-3">
<div class="container">
  <h1>Join Builder</h1>
  <form method="post" class="row g-2 align-items-end">
    <div class="col-md-3">
      <label>Left table</label>
      <select name="table1" class="form-control">
        {% for t in tables %}<option value="{{t}}" {% if t==table1 %}selected{% endif %}>{{t}}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <label>Left col</label>
      <input name="col1" value="{{col1 or ''}}" class="form-control" />
    </div>
    <div class="col-md-2">
      <label>Join</label>
      <select name="jtype" class="form-control"><option>INNER</option><option>LEFT</option><option>RIGHT</option></select>
    </div>
    <div class="col-md-3">
      <label>Right table</label>
      <select name="table2" class="form-control">
        {% for t in tables %}<option value="{{t}}" {% if t==table2 %}selected{% endif %}>{{t}}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <label>Right col</label>
      <input name="col2" value="{{col2 or ''}}" class="form-control" />
    </div>
    <div class="col-12 mt-2">
      <button class="btn btn-primary">Run join</button>
      <a class="btn btn-secondary" href="/">Back</a>
    </div>
  </form>
  <div class="mt-3">
    {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
    {% if table_html %}
      <div class="table-responsive">{{ table_html|safe }}</div>
    {% endif %}
  </div>
</div>
</body>
</html>
'''


@app.route('/')
def index():
    tables = list_tables()
    table = request.values.get('table') or (tables[0] if tables else None)
    rows = int(request.values.get('rows') or 50)
    page = int(request.values.get('page') or 1)
    offset = (page - 1) * rows
    preview_html = ''
    if table:
        conn = get_conn()
        df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT {rows} OFFSET {offset}", conn)
        conn.close()
        preview_html = df.to_html(classes='table table-striped', index=False)
    return render_template_string(INDEX_HTML, tables=tables, table=table, rows=rows, page=page, preview_html=preview_html)


@app.route('/export')
def export():
    table = request.values.get('table')
    rows = int(request.values.get('rows') or 100)
    page = int(request.values.get('page') or 1)
    offset = (page - 1) * rows
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT {rows} OFFSET {offset}", conn)
    conn.close()
    out = io.StringIO()
    df.to_csv(out, index=False)
    return send_file(io.BytesIO(out.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'{table}.csv')


@app.route('/plot')
def plot():
  tables = list_tables()
  table = request.values.get('table') or (tables[0] if tables else None)
  # determine a sensible default column (first column in table)
  column = request.values.get('column')
  try:
    cols = []
    if table:
      conn = get_conn()
      ci = conn.execute(f"PRAGMA table_info({table})").fetchall()
      conn.close()
      cols = [c[1] for c in ci]
  except Exception:
    cols = []
  if not column:
    column = cols[0] if cols else ''
  topn = int(request.values.get('topn') or 20)
  return render_template_string(PLOT_HTML, tables=tables, table=table, column=column, topn=topn)


@app.route('/plot_data')
def plot_data():
  table = request.values.get('table')
  column = request.values.get('column')
  topn = int(request.values.get('topn') or 20)
  if not table or not column:
    return jsonify({'error': 'table and column required'}), 400
  # validate column exists in table
  try:
    conn = get_conn()
    ci = conn.execute(f"PRAGMA table_info({table})").fetchall()
    cols = [c[1] for c in ci]
    conn.close()
  except Exception as e:
    return jsonify({'error': f'Error inspecting table: {e}'}), 500
  if column not in cols:
    return jsonify({'error': f"Column '{column}' not found in table '{table}'", 'available_columns': cols}), 400
  try:
    labels, values = compute_plot_data(table, column, topn)
    return jsonify({'labels': labels, 'values': values})
  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/plot_export')
def plot_export():
  table = request.values.get('table')
  column = request.values.get('column')
  topn = int(request.values.get('topn') or 20)
  labels, values = compute_plot_data(table, column, topn)
  out = io.StringIO()
  writer = csv.writer(out)
  writer.writerow(['label', 'value'])
  for l, v in zip(labels, values):
    writer.writerow([l, v])
  return send_file(io.BytesIO(out.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name=f'plot_{table}_{column}.csv')


def _is_identifier(s):
  return bool(re.match(r'^[A-Za-z0-9_]+$', s))


@app.route('/sql', methods=['GET', 'POST'])
def sql_console():
  query = ''
  table_html = None
  error = None
  if request.method == 'POST':
    query = request.form.get('query', '').strip()
    if not query:
      error = 'Empty query'
    elif ';' in query:
      error = 'Multiple statements are not allowed'
    elif not re.match(r'(?is)^\s*select\b', query):
      error = 'Only SELECT statements are allowed'
    else:
      # ensure a LIMIT exists to protect the server
      if not re.search(r'(?is)\blimit\b', query):
        query = query.rstrip() + ' LIMIT 1000'
      try:
        conn = get_conn()
        df = pd.read_sql_query(query, conn)
        conn.close()
        table_html = df.to_html(classes='table table-striped', index=False)
      except Exception as e:
        error = str(e)
  return render_template_string(SQL_HTML, query=query, table_html=table_html, error=error)


@app.route('/join', methods=['GET', 'POST'])
def join_builder():
  tables = list_tables()
  table1 = request.values.get('table1')
  table2 = request.values.get('table2')
  col1 = request.values.get('col1')
  col2 = request.values.get('col2')
  jtype = request.values.get('jtype') or 'INNER'
  table_html = None
  error = None
  if request.method == 'POST':
    # validate
    if not (table1 and table2 and col1 and col2):
      error = 'Please provide both tables and columns'
    elif not (_is_identifier(table1) and _is_identifier(table2) and _is_identifier(col1) and _is_identifier(col2)):
      error = 'Table and column names must be alphanumeric or underscore only'
    else:
      # restrict unsupported join types (SQLite does not support RIGHT JOIN natively)
      if jtype.upper() not in ('INNER', 'LEFT'):
        error = 'Only INNER and LEFT joins are supported'
      else:
        sql = f"SELECT t1.*, t2.* FROM {table1} t1 {jtype.upper()} JOIN {table2} t2 ON t1.{col1} = t2.{col2} LIMIT 1000"
      try:
        conn = get_conn()
        df = pd.read_sql_query(sql, conn)
        conn.close()
        table_html = df.to_html(classes='table table-striped', index=False)
      except Exception as e:
        error = str(e)
  return render_template_string(JOIN_HTML, tables=tables, table1=table1, table2=table2, col1=col1, col2=col2, jtype=jtype, table_html=table_html, error=error)


def create_app():
    return app
