import os
import datetime
import json
import decimal
import mysql.connector
from config import Config

def backup_db():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join("backups", f"bkdict_backup_{timestamp}.json")
    
    # Ensure backups directory exists
    if not os.path.exists("backups"):
        os.makedirs("backups")
        
    print(f"Starting backup to {backup_file}...")
    
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        backup_data = {}
        
        # Tables to backup
        tables = ['words', 'word_history', 'daily_study_log', 'category_stats']
        
        for table in tables:
            print(f"Backing up table: {table}...")
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            # Helper to serialize date/time/decimal objects
            serialized_rows = []
            for row in rows:
                new_row = {}
                for key, value in row.items():
                    if isinstance(value, (datetime.date, datetime.datetime)):
                        new_row[key] = value.isoformat()
                    elif isinstance(value, decimal.Decimal):
                        new_row[key] = float(value)
                    else:
                        new_row[key] = value
                serialized_rows.append(new_row)
                
            backup_data[table] = serialized_rows
            print(f"  - {len(rows)} records")
            
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n[OK] Backup completed successfully: {backup_file}")
        
    except mysql.connector.Error as err:
        print(f"[ERROR] Database error: {err}")
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    backup_db()
