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
        database=os.environ.get('DB_NAME')
    )
    cursor = conn.cursor()
    
    print("Checking for category_stats view...")
    
    try:
        cursor.execute("SELECT * FROM category_stats LIMIT 5")
        rows = cursor.fetchall()
        print(f"category_stats EXISTS! Found {len(rows)} rows.")
        for row in rows:
            print(f"  {row}")
    except mysql.connector.Error as e:
        print(f"category_stats MISSING or ERROR: {e}")
        
        # Try creating it
        print("\nAttempting to create the view...")
        cursor.execute("""
            CREATE OR REPLACE VIEW category_stats AS
            SELECT
                category,
                COUNT(*) AS word_count,
                MAX(updated_at) AS last_updated
            FROM words
            GROUP BY category
            ORDER BY category
        """)
        conn.commit()
        print("View created successfully!")
        
    conn.close()
except Exception as e:
    print(f"Connection Error: {e}")
