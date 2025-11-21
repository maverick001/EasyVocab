import mysql.connector
from config import Config

def create_trigger():
    conn = None
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        cursor = conn.cursor()

        # Read SQL file
        with open('database/create_trigger.sql', 'r') as f:
            sql_content = f.read()

        # Split commands by delimiter logic (simplified for this specific file)
        # The file uses DELIMITER //, so we need to parse it carefully or just execute the raw parts
        # Since mysql.connector doesn't support DELIMITER syntax directly, we'll split manually
        
        # Drop trigger first
        cursor.execute("DROP TRIGGER IF EXISTS after_review_increment")
        
        # Create trigger
        trigger_sql = """
        CREATE TRIGGER after_review_increment
        AFTER UPDATE ON words
        FOR EACH ROW
        BEGIN
            DECLARE diff INT;
            SET diff = NEW.review_count - OLD.review_count;
            
            IF diff > 0 THEN
                INSERT INTO daily_study_log (date, review_count)
                VALUES (CURDATE(), diff)
                ON DUPLICATE KEY UPDATE review_count = review_count + diff;
            END IF;
        END
        """
        cursor.execute(trigger_sql)
        
        conn.commit()
        print("✓ Trigger 'after_review_increment' created successfully")

    except mysql.connector.Error as err:
        print(f"✗ Error creating trigger: {err}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_trigger()
