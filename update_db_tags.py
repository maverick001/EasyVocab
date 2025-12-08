import mysql.connector
from config import Config
import time

def update_tags():
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        cursor = conn.cursor()
        print("Connected.")

        updates = [
            ('电信_计算机', '电信_IT'),
            ('心理学', '哲学_心理'),
            ('AI', 'AI_CS')
        ]

        total_changed = 0

        for i, (old_tag, new_tag) in enumerate(updates):
            print(f"Updating tag pair {i+1}...")
            
            # Update words table
            cursor.execute("UPDATE words SET category = %s WHERE category = %s", (new_tag, old_tag))
            words_affected = cursor.rowcount
            print(f"  - Updated {words_affected} rows in 'words' table.")
            
            # Update word_history table
            cursor.execute("UPDATE word_history SET category = %s WHERE category = %s", (new_tag, old_tag))
            history_affected = cursor.rowcount
            print(f"  - Updated {history_affected} rows in 'word_history' table.")
            
            total_changed += words_affected

        # Check for any remaining old tags
        print("\nVerifying...")
        for old_tag, _ in updates:
            cursor.execute("SELECT COUNT(*) FROM words WHERE category = %s", (old_tag,))
            count = cursor.fetchone()[0]
            if count == 0:
                print(f"  - Verified: Old tag not found in 'words'.")
            else:
                print(f"  - WARNING: Found {count} instances of old tag in 'words'!")

        # Update category counts
        try:
            print("Updating category_stats...")
            cursor.callproc('update_category_counts')
            print("  - Category stats updated.")
        except mysql.connector.Error as err:
            print(f"  - Note: Could not call 'update_category_counts': {err}")

        conn.commit()
        print("\nDatabase update completed successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    update_tags()
