import mysql.connector
from config import Config

def apply_db_changes():
    print("Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor()

        # 1. Add schema column
        print("Checking/Adding 'last_daily_activity_date' column...")
        try:
            cursor.execute("ALTER TABLE words ADD COLUMN last_daily_activity_date DATE DEFAULT NULL")
            print("  - Column added.")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Duplicate column name
                print("  - Column already exists.")
            else:
                raise err

        # 2. Drop old trigger
        print("Dropping old trigger 'after_review_increment'...")
        cursor.execute("DROP TRIGGER IF EXISTS after_review_increment")
        print("  - Dropped.")

        # 3. Create new trigger
        print("Creating new trigger 'before_word_update_daily_count'...")
        trigger_sql = """
        CREATE TRIGGER before_word_update_daily_count
        BEFORE UPDATE ON words
        FOR EACH ROW
        BEGIN
            -- Check if a "significant" update happened
            IF (NEW.category != OLD.category) OR 
               (NEW.review_count != OLD.review_count) OR
               (NEW.translation != OLD.translation) OR
               ( (NEW.sample_sentence IS NULL AND OLD.sample_sentence IS NOT NULL) OR 
                 (NEW.sample_sentence IS NOT NULL AND OLD.sample_sentence IS NULL) OR
                 (NEW.sample_sentence != OLD.sample_sentence) ) THEN
               
                -- Check if we already counted this word today
                IF (OLD.last_daily_activity_date IS NULL OR OLD.last_daily_activity_date < CURDATE()) THEN
                    -- 1. Increment Daily Log
                    INSERT INTO daily_study_log (date, review_count)
                    VALUES (CURDATE(), 1)
                    ON DUPLICATE KEY UPDATE review_count = review_count + 1;
                    
                    -- 2. Mark word as counted for today
                    SET NEW.last_daily_activity_date = CURDATE();
                END IF;
            END IF;
        END;
        """
        # Drop it first if it exists to be safe (re-runnable)
        cursor.execute("DROP TRIGGER IF EXISTS before_word_update_daily_count")
        cursor.execute(trigger_sql)
        print("  - Created.")

        conn.commit()
        print("\nDatabase changes applied successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    apply_db_changes()
