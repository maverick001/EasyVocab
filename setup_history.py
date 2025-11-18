"""
Setup script to create word_history table
Run this once to add history tracking to your database
"""

import mysql.connector
from config import Config

def setup_word_history():
    """Create word_history table and populate initial data"""

    try:
        # Connect to database
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )

        cursor = connection.cursor()

        print("Creating word_history table...")

        # Create word_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                word_id INT NOT NULL COMMENT 'Reference to words.id',
                word VARCHAR(255) NOT NULL COMMENT 'The word text at this point in time',
                translation TEXT NOT NULL COMMENT 'Translation at this point in time',
                sample_sentence TEXT DEFAULT NULL COMMENT 'Sample sentence at this point in time',
                category VARCHAR(100) NOT NULL COMMENT 'Category at this point in time',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When this version was created',
                modification_type ENUM('created', 'updated', 'moved') NOT NULL DEFAULT 'updated' COMMENT 'Type of modification',

                INDEX idx_word_id (word_id),
                INDEX idx_modified_at (modified_at),
                INDEX idx_word_id_modified (word_id, modified_at DESC)
            ) ENGINE=InnoDB
            DEFAULT CHARSET=utf8mb4
            COLLATE=utf8mb4_unicode_ci
            COMMENT='Word modification history tracking'
        """)

        print("✓ word_history table created")

        # Populate initial history from existing words
        print("Populating initial history records...")

        cursor.execute("""
            INSERT INTO word_history (word_id, word, translation, sample_sentence, category, modified_at, modification_type)
            SELECT
                id,
                word,
                translation,
                sample_sentence,
                category,
                created_at,
                'created'
            FROM words
            WHERE NOT EXISTS (
                SELECT 1 FROM word_history WHERE word_history.word_id = words.id
            )
        """)

        connection.commit()

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM word_history")
        count = cursor.fetchone()[0]

        print(f"✓ Initial history populated: {count} records")
        print("✓ Setup complete!")

        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"✗ Error: {err}")
        raise

if __name__ == '__main__':
    setup_word_history()
