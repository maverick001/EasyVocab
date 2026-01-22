import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

SQL_FILES = [
    'database/init_database.sql',
    'database/update_schema_debt.sql',
    'database/add_review_fields.sql',
    'database/add_word_history.sql',
    'database/create_trigger.sql'
]

BACKUP_FILE = 'backups/bkdict_backup_2025-12-26.sql'

def execute_sql_file(cursor, filepath, encoding='utf-8'):
    print(f"Applying {filepath}...")
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            content = f.read()
            
        # Split by semicolon, but be careful with triggers/procedures
        # Simple implementation: using delimiter logic if present, else split by ;
        
        commands = []
        delimiter = ';'
        buffer = ""
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            if line.upper().startswith('DELIMITER'):
                delimiter = line.split()[1]
                continue
                
            if line.upper().startswith('USE '):
                # INTENTIONAL: Skip USE statements to keep connection on defaultdb
                print(f"  Skipping: {line}")
                continue
                
            buffer += line + " "
            
            if buffer.strip().endswith(delimiter):
                cmd = buffer.strip()
                # Remove delimiter from end
                cmd = cmd[:-len(delimiter)]
                
                if cmd.strip():
                    commands.append(cmd.strip())
                buffer = ""
                
        for cmd in commands:
            try:
                cursor.execute(cmd)
                # Consume results to prevent "Unread result found" error
                if cursor.with_rows:
                    cursor.fetchall()
                # Handle multi-result queries (stored procedures etc)
                while cursor.nextset():
                    if cursor.with_rows:
                        cursor.fetchall()
                        
            except mysql.connector.Error as err:
                if 'already exists' in str(err) or 'Duplicate column' in str(err):
                    print(f"  Note: {err}")
                else:
                    print(f"  ERROR executing: {cmd[:50]}... : {err}")
                    
    except Exception as e:
        print(f"Failed to read/parse {filepath}: {e}")

try:
    print("Connecting to Aiven...")
    conn = mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME')
    )
    cursor = conn.cursor()
    print("Connected!")
    
    # 1. Apply Schema
    for sql_file in SQL_FILES:
        execute_sql_file(cursor, sql_file)
        
    # 2. Try Restore Backup (Optional)
    if os.path.exists(BACKUP_FILE):
        print(f"\nFound backup: {BACKUP_FILE}")
        print("Attempting to restore data (utf-16)...")
        # Note: Backup files often contain USE statements too, we rely on execute_sql_file logic to skip them
        execute_sql_file(cursor, BACKUP_FILE, encoding='utf-16')
    
    conn.commit()
    print("\n✓ Database Initialization Complete!")
    conn.close()
    
except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
