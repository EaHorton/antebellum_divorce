#!/usr/bin/env python3
"""
Safe migration: split People.name entries that contain multiple comma-separated names
into separate People rows. Preserve enslaver_status and enslaver_scope_estimate only
for the first name. Update Petition_People_Lookup to point to the new person_ids.
Creates a timestamped backup before modifying the DB.
"""
import sqlite3
import shutil
import os
import datetime

DB = 'dv_petitions.db'
if not os.path.exists(DB):
    raise SystemExit('Database dv_petitions.db not found in cwd')

# create timestamped backup
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
bak = f"dv_petitions.db.bak.{ts}"
shutil.copy2(DB, bak)
print('Backup created:', bak)

conn = sqlite3.connect(DB)
conn.execute('PRAGMA foreign_keys = OFF')
c = conn.cursor()

# counts before
before_people = c.execute('SELECT COUNT(*) FROM People').fetchone()[0]
before_links = c.execute('SELECT COUNT(*) FROM Petition_People_Lookup').fetchone()[0]
print('Before: People=', before_people, 'Petition_People_Lookup=', before_links)

# read people and links
people = c.execute('SELECT person_id, name, enslaver_status, enslaver_scope_estimate FROM People').fetchall()
links = c.execute('SELECT petition_id, person_id FROM Petition_People_Lookup').fetchall()

old_to_new = {}
for person_id, name, status, scope in people:
    if not name or ',' not in name:
        old_to_new[person_id] = [person_id]
        continue
    parts = [p.strip() for p in name.split(',') if p.strip()]
    created_ids = []
    for i, part in enumerate(parts):
        # preserve enslaver fields ONLY for the first part
        if i == 0:
            es = status
            esc = scope
        else:
            es = None
            esc = None

        # Find existing person with the exact same name and enslaver fields (including NULL)
        if es is None and esc is None:
            row = c.execute(
                "SELECT person_id FROM People WHERE name=? AND enslaver_status IS NULL AND enslaver_scope_estimate IS NULL",
                (part,)
            ).fetchone()
        else:
            # both es/esc may be non-NULL; match exactly
            row = c.execute(
                'SELECT person_id FROM People WHERE name=? AND enslaver_status=? AND enslaver_scope_estimate=?',
                (part, es, esc)
            ).fetchone()

        if row:
            created_ids.append(row[0])
        else:
            # Insert new person; non-first parts will have NULL enslaver fields
            c.execute(
                'INSERT INTO People (name, enslaver_status, enslaver_scope_estimate) VALUES (?, ?, ?)',
                (part, es, esc)
            )
            created_ids.append(c.lastrowid)
    old_to_new[person_id] = created_ids

# Rebuild petition-person links
for petition_id, old_person_id in links:
    mapped = old_to_new.get(old_person_id, [old_person_id])
    for new_pid in mapped:
        c.execute('INSERT OR IGNORE INTO Petition_People_Lookup (petition_id, person_id) VALUES (?, ?)', (petition_id, new_pid))

# delete original multi-name people rows
for person_id, name, status, scope in people:
    if name and ',' in name:
        c.execute('DELETE FROM People WHERE person_id=?', (person_id,))

conn.commit()

# counts after
after_people = c.execute('SELECT COUNT(*) FROM People').fetchone()[0]
after_links = c.execute('SELECT COUNT(*) FROM Petition_People_Lookup').fetchone()[0]
print('After: People=', after_people, 'Petition_People_Lookup=', after_links)

# run a simple check for any names still containing commas
still = c.execute("SELECT COUNT(*) FROM People WHERE name LIKE '%,%'").fetchone()[0]
print('Remaining People rows with commas in name:', still)

conn.close()
print('Migration finished.')
