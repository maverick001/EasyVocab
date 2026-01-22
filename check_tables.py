import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

print(f"Connecting to: {os.environ.get('DB_HOST')}")

try:
    conn = mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME')
    )
    cursor = conn.cursor()
    
    print("\n--- TABLES IN DB ---")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    if not tables:
        print("[EMPTY] No tables found.")
    else:
        for (table_name,) in tables:
            print(f"- {table_name}")
            
            # Check row count for key tables
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")

    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
