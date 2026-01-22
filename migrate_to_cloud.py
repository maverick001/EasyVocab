# migrate_to_cloud.py
# Migrates data from local MySQL to Aiven Cloud with proper UTF-8 encoding

import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

# Local MySQL credentials (the original database)
LOCAL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Wader008',
    'database': 'bkdict_db',
    'charset': 'utf8mb4'
}

# Cloud Aiven credentials (from .env)
CLOUD_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'charset': 'utf8mb4'
}

def migrate():
    print("=== Migration: Local MySQL -> Aiven Cloud ===\n")
    
    # 1. Connect to LOCAL
    print("Connecting to LOCAL MySQL...")
    local_conn = mysql.connector.connect(**LOCAL_CONFIG)
    local_cursor = local_conn.cursor(dictionary=True)
    print("  Connected!")
    
    # 2. Connect to CLOUD
    print("Connecting to CLOUD (Aiven)...")
    cloud_conn = mysql.connector.connect(**CLOUD_CONFIG)
    cloud_cursor = cloud_conn.cursor()
    print("  Connected!")
    
    # 3. Clear cloud data
    print("\nClearing corrupted cloud data...")
    cloud_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    cloud_cursor.execute("TRUNCATE TABLE word_history")
    cloud_cursor.execute("TRUNCATE TABLE words")
    cloud_cursor.execute("TRUNCATE TABLE categories")
    cloud_cursor.execute("TRUNCATE TABLE daily_study_log")
    cloud_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    cloud_conn.commit()
    print("  Cleared!")
    
    # 4. Migrate 'words' table
    print("\nMigrating 'words' table...")
    local_cursor.execute("SELECT * FROM words")
    words = local_cursor.fetchall()
    print(f"  Found {len(words)} words in local DB.")
    
    if words:
        # Get column names from first row
        columns = list(words[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        col_names = ', '.join(columns)
        
        insert_sql = f"INSERT INTO words ({col_names}) VALUES ({placeholders})"
        
        batch_size = 500
        for i in range(0, len(words), batch_size):
            batch = words[i:i+batch_size]
            values = [tuple(row.values()) for row in batch]
            cloud_cursor.executemany(insert_sql, values)
            cloud_conn.commit()
            print(f"  Migrated {min(i+batch_size, len(words))}/{len(words)} words...")
    
    # 5. Migrate 'daily_study_log' table
    print("\nMigrating 'daily_study_log' table...")
    try:
        local_cursor.execute("SELECT * FROM daily_study_log")
        logs = local_cursor.fetchall()
        print(f"  Found {len(logs)} log entries.")
        
        for log in logs:
            cloud_cursor.execute(
                "INSERT INTO daily_study_log (date, review_count) VALUES (%s, %s)",
                (log['date'], log['review_count'])
            )
        cloud_conn.commit()
    except Exception as e:
        print(f"  Skipped (table might not exist locally): {e}")
    
    # 6. Recreate category_stats view
    print("\nRecreating category_stats view...")
    cloud_cursor.execute("""
        CREATE OR REPLACE VIEW category_stats AS
        SELECT
            category,
            COUNT(*) AS word_count,
            MAX(updated_at) AS last_updated
        FROM words
        GROUP BY category
        ORDER BY category
    """)
    cloud_conn.commit()
    print("  View created!")
    
    # 7. Verify
    print("\n=== Verification ===")
    cloud_cursor.execute("SELECT COUNT(*) FROM words")
    count = cloud_cursor.fetchone()[0]
    print(f"  Words in cloud: {count}")
    
    cloud_cursor.execute("SELECT DISTINCT category FROM words LIMIT 5")
    cats = cloud_cursor.fetchall()
    print("  Sample categories:")
    for (cat,) in cats:
        print(f"    '{cat}'")
    
    # Cleanup
    local_conn.close()
    cloud_conn.close()
    
    print("\n✓ Migration Complete!")

if __name__ == '__main__':
    migrate()
