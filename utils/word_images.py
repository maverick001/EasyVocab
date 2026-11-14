"""
Shared definition of the word_images table.

Used by app.py (ensure_word_images_table) and scripts/migrate_images_to_mysql.py,
so the schema is written once.
"""

# Same collation as words.image_file, so the two compare directly.
CREATE_WORD_IMAGES_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS word_images (
        filename VARCHAR(255) NOT NULL,
        mime_type VARCHAR(50) NOT NULL,
        data MEDIUMBLOB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (filename)
    ) ENGINE=InnoDB
    DEFAULT CHARSET=utf8mb4
    COLLATE=utf8mb4_unicode_ci
    COMMENT='Word image bytes, keyed by words.image_file / image_file_2'
"""
