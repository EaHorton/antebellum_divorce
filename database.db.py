import csv
import sqlite3
import os
from collections import defaultdict
import argparse
import shutil
import datetime

CSV_PATH = '/Users/eahorton/Downloads/nc_al_tn_clean_data.csv'
DB_PATH = 'dv_petitions.db'

# Read CSV and clean whitespace from headers and cells
rows = []
with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    # Clean header names
    reader.fieldnames = [h.strip() for h in reader.fieldnames]
    for row in reader:
        clean_row = {k.strip(): v.strip() for k, v in row.items()}
        rows.append(clean_row)

# --- Petitions Table ---
petitions = []
petition_id_map = {}
for idx, row in enumerate(rows, 1):
    petition_id_map[row['parcel_number']] = idx
    petitions.append((
        idx,
        row['parcel_number'],
        row['archive'],
        row['petitioner'],
        row['defendant'],
        row['month'],
        row['year'],
        row['county'],
        row['state'],
        row['years_married'],
        row.get('additional_requests')
    ))

# --- Reasoning Table ---
reasoning_set = set()
reasoning = []
reasoning_id_map = {}
reasoning_id_counter = 1
for row in rows:
    terms = [t.strip() for t in row['reasoning'].split(',') if t.strip()]
    for term in terms:
        if term and term not in reasoning_set:
            reasoning_set.add(term)
            reasoning_id_map[term] = reasoning_id_counter
            reasoning.append((reasoning_id_counter, term))
            reasoning_id_counter += 1

# --- Petition_Reasoning_Lookup Table ---
petition_reasoning_lookup = []
for idx, row in enumerate(rows, 1):
    terms = [t.strip() for t in row['reasoning'].split(',') if t.strip()]
    for term in terms:
        reasoning_id = reasoning_id_map.get(term)
        if reasoning_id:
            petition_reasoning_lookup.append((idx, reasoning_id))

# --- People Table ---
people_set = set()
people = []
person_id_map = {}
person_id_counter = 1
for row in rows:
    enslaver_status = row.get('enslaver_status', '')
    enslaver_scope = row.get('enslaver_scope_estimate', '')
    for role in ['petitioner', 'defendant']:
        name = row[role]
        key = (name, enslaver_status, enslaver_scope)
        if name and key not in people_set:
            people_set.add(key)
            person_id_map[key] = person_id_counter
            people.append((person_id_counter, name, enslaver_status, enslaver_scope))
            person_id_counter += 1

# --- Petition_People_Lookup Table ---
lookup = []
for row in rows:
    parcel = row['parcel_number']
    pid = petition_id_map[parcel]
    enslaver_status = row.get('enslaver_status', '')
    enslaver_scope = row.get('enslaver_scope_estimate', '')
    for role in ['petitioner', 'defendant']:
        name = row[role]
        key = (name, enslaver_status, enslaver_scope)
        if name:
            lookup.append((pid, person_id_map[key]))

# --- Reasoning Table ---
reasoning_set = set()
reasoning = []
reasoning_id_map = {}
reasoning_id_counter = 1
for row in rows:
    terms = [t.strip() for t in row['reasoning'].split(',') if t.strip()]
    for term in terms:
        if term and term not in reasoning_set:
            reasoning_set.add(term)
            reasoning_id_map[term] = reasoning_id_counter
            reasoning.append((reasoning_id_counter, term))
            reasoning_id_counter += 1

# --- Archive Lookup Table ---
archive_set = set()
archive = []
archive_id_map = {}
archive_id_counter = 1
for row in rows:
    arch = row['archive'].strip()
    if arch and arch not in archive_set:
        archive_set.add(arch)
        archive_id_map[arch] = archive_id_counter
        archive.append((archive_id_counter, arch))
        archive_id_counter += 1

# --- Court Table ---
court_set = set()
court = []
for row in rows:
    key = (row['end_court'], row['county'], row['state'])
    if key not in court_set:
        court_set.add(key)
        court.append(key)

# --- Additional Requests Table ---
addreq_set = set()
addreq = []
addreq_id_map = {}
addreq_id_counter = 1
for row in rows:
    req = row['additional_requests'].strip()
    if req and req not in addreq_set:
        addreq_set.add(req)
        addreq_id_map[req] = addreq_id_counter
        addreq.append((addreq_id_counter, req))
        addreq_id_counter += 1

# --- Create SQLite DB ---
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
# Enforce foreign key constraints
c.execute('PRAGMA foreign_keys = ON')

c.execute('''CREATE TABLE Petitions (
    petition_id INTEGER PRIMARY KEY,
    parcel_number TEXT,
    archive TEXT,
    petitioner TEXT,
    defendant TEXT,
    month TEXT,
    year TEXT,
    county TEXT,
    state TEXT,
    years_married TEXT,
    additional_requests_id INTEGER,
    FOREIGN KEY(additional_requests_id) REFERENCES Additional_Requests(additional_requests_id)
)''')
c.execute('''CREATE TABLE Petition_Reasoning_Lookup (
    petition_id INTEGER,
    reasoning_id INTEGER
)''')
c.execute('''CREATE TABLE People (
    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    enslaver_status TEXT,
    enslaver_scope_estimate TEXT,
    UNIQUE(name, enslaver_status, enslaver_scope_estimate)
)''')
c.execute('''CREATE TABLE Petition_People_Lookup (
    petition_id INTEGER,
    person_id INTEGER
)''')
c.execute('''CREATE TABLE Reasoning (
    reasoning_id INTEGER PRIMARY KEY,
    reasoning TEXT
)''')
c.execute('''CREATE TABLE Archive_Lookup (
    archive_id INTEGER PRIMARY KEY,
    archive TEXT
)''')
c.execute('''CREATE TABLE Court (
    court TEXT,
    county TEXT,
    state TEXT
)''')
c.execute('''CREATE TABLE Additional_Requests (
    additional_requests_id INTEGER PRIMARY KEY AUTOINCREMENT,
    additional_requests TEXT UNIQUE
)''')

# Insert Reasoning, Archive, Court lookup rows
c.executemany('INSERT INTO Reasoning VALUES (?, ?)', reasoning)
c.executemany('INSERT INTO Archive_Lookup VALUES (?, ?)', archive)
c.executemany('INSERT INTO Court VALUES (?, ?, ?)', court)

# Insert people using INSERT OR IGNORE and build a mapping from (name,status,scope) -> person_id
person_key_to_id = {}
for _pid, name, status, scope in people:
    key = (name, status, scope)
    c.execute('INSERT OR IGNORE INTO People (name, enslaver_status, enslaver_scope_estimate) VALUES (?, ?, ?)', (name, status, scope))
    c.execute('SELECT person_id FROM People WHERE name=? AND enslaver_status=? AND enslaver_scope_estimate=?', (name, status, scope))
    person_key_to_id[key] = c.fetchone()[0]

# Rebuild Petition_People_Lookup using mapped person_ids (we'll insert after Petitions are created)
new_lookup = []
for row in rows:
    parcel = row['parcel_number']
    pid = petition_id_map[parcel]
    enslaver_status = row.get('enslaver_status', '')
    enslaver_scope = row.get('enslaver_scope_estimate', '')
    for role in ['petitioner', 'defendant']:
        name = row[role]
        key = (name, enslaver_status, enslaver_scope)
        new_person_id = person_key_to_id.get(key)
        if new_person_id:
            new_lookup.append((pid, new_person_id))


# --- Split Additional Requests into separate rows ---
split_addreq = []
for addreq_id, req in addreq:
    if req:
        requests = [r.strip() for r in req.split(',') if r.strip()]
        for r in requests:
            split_addreq.append((addreq_id, r))

# Overwrite the Additional_Requests table with split entries
c.execute('DROP TABLE IF EXISTS Additional_Requests')
c.execute('''CREATE TABLE Additional_Requests (
    additional_requests_id INTEGER PRIMARY KEY AUTOINCREMENT,
    additional_requests TEXT UNIQUE
)''')
# Insert only the split request text; allow the DB to assign unique IDs
texts = [(r,) for (_aid, r) in split_addreq]
c.executemany('INSERT OR IGNORE INTO Additional_Requests (additional_requests) VALUES (?)', texts)

# Build a map from the inserted additional_requests text -> their new autoincremented id
addreq_text_to_id = {}
for aid, text in c.execute('SELECT additional_requests_id, additional_requests FROM Additional_Requests'):
    if text:
        addreq_text_to_id[text.lower()] = aid


# Now insert Petitions with mapped additional_requests_id
petitions_mapped = []
for pet in petitions:
    addreq_text = pet[-1]
    addreq_id = None
    if addreq_text and isinstance(addreq_text, str):
        parts = [p.strip().lower() for p in addreq_text.split(',') if p.strip()]
        for p in parts:
            if p in addreq_text_to_id:
                addreq_id = addreq_text_to_id[p]
                break
    petitions_mapped.append((pet[0], pet[1], pet[2], pet[3], pet[4], pet[5], pet[6], pet[7], pet[8], pet[9], addreq_id))

c.executemany('INSERT INTO Petitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', petitions_mapped)

# Insert petition_reasoning_lookup (after Petitions exist)
c.executemany('INSERT INTO Petition_Reasoning_Lookup VALUES (?, ?)', petition_reasoning_lookup)

# Insert Petition_People_Lookup using mapped person IDs
c.executemany('INSERT OR IGNORE INTO Petition_People_Lookup VALUES (?, ?)', new_lookup)

# --- Result Table ---
result_rows = []
for idx, row in enumerate(rows, start=1):
    result_cell = row.get('result')
    if result_cell:
        results = [r.strip() for r in result_cell.split(',') if r.strip()]
        for res in results:
            # Rename "denied" to "rejected"
            if res.lower() == 'denied':
                res = 'rejected'
            result_rows.append((idx, res))

c.execute('DROP TABLE IF EXISTS Result')
c.execute('''CREATE TABLE Result (
    petition_id INTEGER,
    result TEXT
)''')
c.executemany('INSERT INTO Result VALUES (?, ?)', result_rows)


conn.commit()
conn.close()
print('Database created as', DB_PATH)

def split_people_rows(db_path=DB_PATH):
    """
    Migration: if any `People.name` contains multiple names separated by commas,
    split them into separate People rows and update Petition_People to point to
    the new person_id values. Preserves enslaver_status and enslaver_scope_estimate.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Read existing people and petition links
    people = c.execute('SELECT person_id, name, enslaver_status, enslaver_scope_estimate FROM People').fetchall()
    # table is Petition_People_Lookup with columns (petition_id, person_id)
    links = c.execute('SELECT petition_id, person_id FROM Petition_People_Lookup').fetchall()

    # Build mapping from old person_id -> list of new person_ids
    new_people = []  # tuples (name, status, scope)
    old_to_new = {}  # old_id -> [new_id, ...]

    for person_id, name, status, scope in people:
        parts = [p.strip() for p in (name or '').split(',') if p.strip()]
        if len(parts) <= 1:
            # keep as-is
            old_to_new[person_id] = [person_id]
            continue
        # for multi-name entries, create new rows
        created_ids = []
        for i, part in enumerate(parts):
            # preserve enslaver fields only for the first name
            if i == 0:
                es = status
                esc = scope
            else:
                es = None
                esc = None
            c.execute('INSERT INTO People (name, enslaver_status, enslaver_scope_estimate) VALUES (?, ?, ?)',
                      (part, es, esc))
            created_ids.append(c.lastrowid)
        old_to_new[person_id] = created_ids

    # Now rebuild Petition_People_Lookup: insert links for new person_ids
    for petition_id, person_id in links:
        mapped = old_to_new.get(person_id, [person_id])
        for new_id in mapped:
            c.execute('INSERT OR IGNORE INTO Petition_People_Lookup (petition_id, person_id) VALUES (?, ?)',
                      (petition_id, new_id))

    # Remove any original rows that had multiple names (to avoid duplicates)
    for person_id, name, status, scope in people:
        parts = [p.strip() for p in (name or '').split(',') if p.strip()]
        if len(parts) > 1:
            c.execute('DELETE FROM People WHERE person_id=?', (person_id,))

    conn.commit()
    conn.close()
    print('Split multi-name People rows and updated Petition_People links.')


def migrate_people_inplace(db_path=DB_PATH):
    """Safe in-place migration wrapper: creates a timestamped backup then runs the
    split logic using the same semantics as split_people_rows()."""
    if not os.path.exists(db_path):
        raise SystemExit(f"Database {db_path} not found")
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, bak)
    print('Backup created:', bak)

    # Disable foreign keys while we mutate link tables
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = OFF')
    c = conn.cursor()

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
            if i == 0:
                es = status
                esc = scope
            else:
                es = None
                esc = None

            if es is None and esc is None:
                row = c.execute(
                    "SELECT person_id FROM People WHERE name=? AND enslaver_status IS NULL AND enslaver_scope_estimate IS NULL",
                    (part,)
                ).fetchone()
            else:
                row = c.execute(
                    'SELECT person_id FROM People WHERE name=? AND enslaver_status=? AND enslaver_scope_estimate=?',
                    (part, es, esc)
                ).fetchone()

            if row:
                created_ids.append(row[0])
            else:
                c.execute(
                    'INSERT INTO People (name, enslaver_status, enslaver_scope_estimate) VALUES (?, ?, ?)',
                    (part, es, esc)
                )
                created_ids.append(c.lastrowid)

        old_to_new[person_id] = created_ids

    for petition_id, old_person_id in links:
        mapped = old_to_new.get(old_person_id, [old_person_id])
        for new_pid in mapped:
            c.execute('INSERT OR IGNORE INTO Petition_People_Lookup (petition_id, person_id) VALUES (?, ?)', (petition_id, new_pid))

    for person_id, name, status, scope in people:
        if name and ',' in name:
            c.execute('DELETE FROM People WHERE person_id=?', (person_id,))

    conn.commit()
    conn.close()
    print('In-place people migration completed.')


def main():
    parser = argparse.ArgumentParser(description='Create normalized dv_petitions.db and optionally run migrations')
    parser.add_argument('--migrate-people', action='store_true', help='Run People-splitting migration in-place (creates backup)')
    args = parser.parse_args()

    if args.migrate_people:
        migrate_people_inplace(DB_PATH)
        return


if __name__ == '__main__':
    main()
