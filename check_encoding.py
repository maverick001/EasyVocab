import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME'),
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    
    print("=== Database Encoding Check ===\n")
    
    # Check database/table charset
    cursor.execute("SHOW VARIABLES LIKE 'character_set%'")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")
    
    print("\n=== Sample Data ===")
    cursor.execute("SELECT category FROM words LIMIT 5")
    for row in cursor.fetchall():
        print(f"Category: {row[0]} | Bytes: {row[0].encode('utf-8') if row[0] else 'N/A'}")
    
    print("\n=== Distinct Categories ===")
    cursor.execute("SELECT DISTINCT category FROM words LIMIT 10")
    for (cat,) in cursor.fetchall():
        print(f"  '{cat}'")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
