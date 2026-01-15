
import sqlite3
import os

DB_NAME = 'bkdict.db'

def migrate():
    print(f"Checking database: {DB_NAME}")
    if not os.path.exists(DB_NAME):
        print("Database file not found!")
        return

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check columns
        columns_to_add = [
            ("next_review_date", "DATETIME DEFAULT NULL"),
            ("srs_interval", "INT DEFAULT 0"),
            ("srs_repetitions", "INT DEFAULT 0"),
            ("srs_ease_factor", "FLOAT DEFAULT 2.5")
        ]
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(words)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        for col_name, col_def in columns_to_add:
            if col_name not in existing_cols:
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE words ADD COLUMN {col_name} {col_def}")
                print(f"  + Added {col_name}")
            else:
                print(f"  - Column {col_name} already exists")
                
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
