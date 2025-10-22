import sqlite3
import os
from typing import List, Tuple

# Resolve the DB path relative to the repository root (one level up from this file)
HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(HERE, '..', 'dv_petitions.db'))


def get_conn(path: str = None):
    path = path or DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"SQLite DB not found at {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def list_tables(path: str = None) -> List[str]:
    conn = get_conn(path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables


def table_count(table: str, path: str = None) -> int:
    conn = get_conn(path)
    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
    v = cur.fetchone()[0]
    conn.close()
    return v


def sample_rows(table: str, limit: int = 10, offset: int = 0, path: str = None):
    conn = get_conn(path)
    cur = conn.execute(f"SELECT * FROM {table} LIMIT {limit} OFFSET {offset}")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def compute_plot_data(table: str, column: str, topn: int = 20, path: str = None):
    """Return (labels, values) for the given table/column (top N)."""
    conn = get_conn(path)
    try:
        dfc = None
        import pandas as _pd
        dfc = _pd.read_sql_query(f"SELECT {column} FROM {table}", conn)
        counts = dfc[column].fillna('NULL').astype(str).value_counts().head(topn)
        labels = counts.index.tolist()
        values = counts.values.tolist()
        return labels, values
    finally:
        conn.close()
