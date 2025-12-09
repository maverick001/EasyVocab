import mysql.connector
from config import Config
import time

def test_daily_logic():
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        
        # 0. Get current daily count
        cursor.execute("SELECT review_count FROM daily_study_log WHERE date = CURDATE()")
        res = cursor.fetchone()
        initial_daily_count = res['review_count'] if res else 0
        print(f"Initial Daily Count: {initial_daily_count}")

        # 1. Create a dummy test word
        print("\nCreating test word...")
        cursor.execute("INSERT INTO words (word, translation, category, review_count) VALUES ('TEST_WORD_DAILY', 'Test', 'TestCat', 0)")
        word_id = cursor.lastrowid
        conn.commit()
        print(f"Created word ID: {word_id}")

        # 2. Action 1: Change Category (Should Increment)
        print("\n[Action 1] Changing Category (EXPECT: +1)")
        cursor.execute("UPDATE words SET category = 'NewCat' WHERE id = %s", (word_id,))
        conn.commit()
        
        # Check count
        cursor.execute("SELECT review_count FROM daily_study_log WHERE date = CURDATE()")
        count_after_1 = cursor.fetchone()['review_count']
        print(f"  - Count: {count_after_1} (Diff: {count_after_1 - initial_daily_count})")
        
        # 3. Action 2: Review 'Remember' (Should NOT Increment - already counted)
        print("\n[Action 2] Review 'Remember' (Count -1) (EXPECT: +0)")
        cursor.execute("UPDATE words SET review_count = review_count - 1 WHERE id = %s", (word_id,))
        conn.commit()
        
        # Check count
        cursor.execute("SELECT review_count FROM daily_study_log WHERE date = CURDATE()")
        count_after_2 = cursor.fetchone()['review_count']
        print(f"  - Count: {count_after_2} (Diff: {count_after_2 - count_after_1})")

        # 4. Action 3: Edit Translation (Should NOT Increment - already counted)
        print("\n[Action 3] Edit Translation (EXPECT: +0)")
        cursor.execute("UPDATE words SET translation = 'NewTrans' WHERE id = %s", (word_id,))
        conn.commit()
        
        # Check count
        cursor.execute("SELECT review_count FROM daily_study_log WHERE date = CURDATE()")
        count_after_3 = cursor.fetchone()['review_count']
        print(f"  - Count: {count_after_3} (Diff: {count_after_3 - count_after_2})")
        
        # Cleanup
        print("\nCleaning up...")
        cursor.execute("DELETE FROM words WHERE id = %s", (word_id,))
        conn.commit()
        print("Done.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    test_daily_logic()
