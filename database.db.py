import csv
import sqlite3
import os
from collections import defaultdict

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
        row['result'],
        row['years_married'],
        row['additional_requests']
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
    result TEXT,
    years_married TEXT,
    additional_requests TEXT
)''')
c.execute('''CREATE TABLE Petition_Reasoning_Lookup (
    petition_id INTEGER,
    reasoning_id INTEGER
)''')
c.execute('''CREATE TABLE People (
    person_id INTEGER PRIMARY KEY,
    name TEXT,
    enslaver_status TEXT,
    enslaver_scope_estimate TEXT
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
    additional_requests_id INTEGER,
    additional_requests TEXT
)''')

c.executemany('INSERT INTO Petitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', petitions)
c.executemany('INSERT INTO Petition_Reasoning_Lookup VALUES (?, ?)', petition_reasoning_lookup)
c.executemany('INSERT INTO People VALUES (?, ?, ?, ?)', people)
c.executemany('INSERT INTO Petition_People_Lookup VALUES (?, ?)', lookup)
c.executemany('INSERT INTO Reasoning VALUES (?, ?)', reasoning)
c.executemany('INSERT INTO Archive_Lookup VALUES (?, ?)', archive)
c.executemany('INSERT INTO Court VALUES (?, ?, ?)', court)


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
    additional_requests_id INTEGER,
    additional_requests TEXT
)''')
c.executemany('INSERT INTO Additional_Requests VALUES (?, ?)', split_addreq)

# --- Result Table ---
result_rows = []
for petition in petitions:
    petition_id = petition[0]
    result_cell = petition[9]  # result column
    if result_cell:
        results = [r.strip() for r in result_cell.split(',') if r.strip()]
        for res in results:
         # Rename "denied" to "rejected"
            if res.lower() == "denied":
                res = "rejected"
            result_rows.append((petition_id, res))

c.execute('DROP TABLE IF EXISTS Result')
c.execute('''CREATE TABLE Result (
    petition_id INTEGER,
    result TEXT
)''')
c.executemany('INSERT INTO Result VALUES (?, ?)', result_rows)


conn.commit()
conn.close()
print('Database created as', DB_PATH)
