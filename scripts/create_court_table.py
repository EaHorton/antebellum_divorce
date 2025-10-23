import sqlite3
from datetime import datetime

def create_backup(db_path):
    """Create a backup of the database before making changes"""
    import shutil
    backup_path = f"{db_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def create_court_table(conn):
    """Create the new Court table"""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Court (
        court_id INTEGER PRIMARY KEY AUTOINCREMENT,
        court_name TEXT UNIQUE NOT NULL
    )
    ''')
    conn.commit()

def populate_court_table(conn):
    """Extract unique courts from Petitions and populate Court table"""
    cursor = conn.cursor()
    
    # Get all unique court names from Petitions
    cursor.execute('SELECT DISTINCT court FROM Petitions WHERE court IS NOT NULL')
    courts = cursor.fetchall()
    
    # Insert courts into Court table
    for court in courts:
        cursor.execute('INSERT OR IGNORE INTO Court (court_name) VALUES (?)', (court[0],))
    
    conn.commit()
    print(f"Added {len(courts)} unique courts to Court table")

def add_court_id_to_petitions(conn):
    """Add court_id column to Petitions table"""
    cursor = conn.cursor()
    
    # Get the list of columns in Petitions table
    cursor.execute('PRAGMA table_info(Petitions)')
    columns = cursor.fetchall()
    
    # Check if court_id column exists
    if 'court_id' not in [col[1] for col in columns]:
        # Add new column only if it doesn't exist
        cursor.execute('ALTER TABLE Petitions ADD COLUMN court_id INTEGER')
    
    # Update court_id based on court names
    cursor.execute('''
    UPDATE Petitions 
    SET court_id = (
        SELECT court_id 
        FROM Court 
        WHERE Court.court_name = Petitions.court
    )
    WHERE court IS NOT NULL
    ''')
    
    # Add foreign key constraint
    cursor.execute('''
    CREATE TABLE Petitions_new (
        petition_id INTEGER PRIMARY KEY,
        parcel_number TEXT,
        archive TEXT,
        month TEXT,
        year TEXT,
        county TEXT,
        state TEXT,
        years_married TEXT,
        court TEXT,
        additional_requests_id INTEGER,
        petitioner_id INTEGER,
        defendant_id INTEGER,
        court_id INTEGER,
        FOREIGN KEY(additional_requests_id) REFERENCES Additional_Requests(additional_requests_id),
        FOREIGN KEY(petitioner_id) REFERENCES People(person_id),
        FOREIGN KEY(defendant_id) REFERENCES People(person_id),
        FOREIGN KEY(court_id) REFERENCES Court(court_id)
    )
    ''')
    
    # Copy data to new table
    cursor.execute('''
    INSERT INTO Petitions_new 
    SELECT 
        petition_id,
        parcel_number,
        archive,
        month,
        year,
        county,
        state,
        years_married,
        court,
        additional_requests_id,
        petitioner_id,
        defendant_id,
        court_id
    FROM Petitions
    ''')
    
    # Drop old table and rename new one
    cursor.execute('DROP TABLE Petitions')
    cursor.execute('ALTER TABLE Petitions_new RENAME TO Petitions')
    
    conn.commit()
    print("Updated Petitions table with court_id foreign key")

def verify_migration(conn):
    """Verify that the migration was successful"""
    cursor = conn.cursor()
    
    # Check Court table
    cursor.execute('SELECT COUNT(*) FROM Court')
    court_count = cursor.fetchone()[0]
    print(f"Number of courts in Court table: {court_count}")
    
    # Check Petitions table court_id mapping
    cursor.execute('''
    SELECT COUNT(*) 
    FROM Petitions p 
    LEFT JOIN Court c ON p.court_id = c.court_id
    WHERE p.court_id IS NOT NULL
    ''')
    mapped_count = cursor.fetchone()[0]
    print(f"Number of petitions with mapped court_id: {mapped_count}")

def main():
    db_path = '../dv_petitions.db'
    
    # Create backup
    backup_path = create_backup(db_path)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    try:
        # Execute migration steps
        print("Creating Court table...")
        create_court_table(conn)
        
        print("\nPopulating Court table...")
        populate_court_table(conn)
        
        print("\nUpdating Petitions table...")
        add_court_id_to_petitions(conn)
        
        print("\nVerifying migration...")
        verify_migration(conn)
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        print(f"You can restore from backup at: {backup_path}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()