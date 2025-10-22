#!/usr/bin/env python3
"""CLI for exploring dv_petitions.db (no Streamlit required).

Commands:
  list-tables
  preview --table Petitions --rows 50 --page 1
  query --name reasoning_by_state
  plot --table Petitions --column state --topn 20 --format csv

"""
import argparse
import json
import csv
import sys
from pathlib import Path
from . import __version__
from .db_helper import list_tables, sample_rows, table_count, compute_plot_data, get_conn


PREBUILT = {
    'reasoning_by_state': {
        'label': 'Most common reasoning by state',
        'sql': """
SELECT p.state, r.reasoning, COUNT(*) as cnt
FROM Petitions p
JOIN Petition_Reasoning_Lookup pr ON p.petition_id = pr.petition_id
JOIN Reasoning r ON pr.reasoning_id = r.reasoning_id
GROUP BY p.state, r.reasoning
ORDER BY p.state, cnt DESC
"""
    },
    'counts_by_result': {
        'label': 'Counts by state and result',
        'sql': "SELECT p.state, r.result, COUNT(*) as cnt FROM Petitions p JOIN Result r ON p.petition_id = r.petition_id GROUP BY p.state, r.result ORDER BY p.state, cnt DESC"
    },
    'top_petitioners': {
        'label': 'Top petitioners (people)',
        'sql': "SELECT pe.name, COUNT(*) cnt FROM People pe JOIN Petition_People_Lookup ppl ON pe.person_id = ppl.person_id GROUP BY pe.name ORDER BY cnt DESC"
    }
}


def cmd_list_tables(args):
    for t in list_tables():
        print(t)


def cmd_preview(args):
    rows = args.rows
    page = args.page
    offset = (page - 1) * rows
    rows_data = sample_rows(args.table, limit=rows, offset=offset)
    # print as CSV to stdout
    if not rows_data:
        print('No rows')
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows_data[0].keys()))
    writer.writeheader()
    writer.writerows(rows_data)


def cmd_query(args):
    name = args.name
    if name not in PREBUILT:
        print('Unknown query:', name)
        return 1
    sql = PREBUILT[name]['sql']
    conn = get_conn()
    cur = conn.execute(sql)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if args.format == 'json':
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print('No rows')
            return
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def cmd_plot(args):
    labels, values = compute_plot_data(args.table, args.column, args.topn)
    rows = [{'label': l, 'value': v} for l, v in zip(labels, values)]
    if args.format == 'json':
        print(json.dumps(rows, indent=2))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=['label', 'value'])
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    p = argparse.ArgumentParser(prog='dvcli')
    p.add_argument('--version', action='store_true')
    sub = p.add_subparsers(dest='cmd')

    sub.add_parser('list-tables')

    pv = sub.add_parser('preview')
    pv.add_argument('--table', required=True)
    pv.add_argument('--rows', type=int, default=50)
    pv.add_argument('--page', type=int, default=1)

    q = sub.add_parser('query')
    q.add_argument('--name', required=True, choices=list(PREBUILT.keys()))
    q.add_argument('--format', choices=['csv', 'json'], default='csv')

    pl = sub.add_parser('plot')
    pl.add_argument('--table', required=True)
    pl.add_argument('--column', required=True)
    pl.add_argument('--topn', type=int, default=20)
    pl.add_argument('--format', choices=['csv', 'json'], default='csv')

    sf = sub.add_parser('serve-flask')
    sf.add_argument('--host', default='127.0.0.1')
    sf.add_argument('--port', type=int, default=8501)

    args = p.parse_args(argv)
    if args is None:
        p.print_help()
        return
    if getattr(args, 'version', False):
        print(__version__)
        return
    if args.cmd == 'list-tables':
        return cmd_list_tables(args)
    if args.cmd == 'preview':
        return cmd_preview(args)
    if args.cmd == 'query':
        return cmd_query(args)
    if args.cmd == 'plot':
        return cmd_plot(args)
    if args.cmd == 'serve-flask':
        # Import and serve the Flask app from the package context
        from .webapp import create_app
        flask_app = create_app()
        print(f"Serving Flask app on http://{args.host}:{args.port}")
        flask_app.run(host=args.host, port=args.port, debug=True)
    p.print_help()


if __name__ == '__main__':
    raise SystemExit(main())
