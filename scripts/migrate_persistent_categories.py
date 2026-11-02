"""
One-off migration: make the categories table the source of truth for which
categories exist, so an empty category stays listed until it is deleted.

What it does (safe to run more than once):
  1. Creates the 未分组单词 category row, which deleted categories move words into.
  2. Replaces update_category_counts() with a version that updates counts in
     place instead of TRUNCATE-ing the categories table. The old version is
     what made a category vanish when its last word was deleted.
  3. Runs the new procedure once so counts and rows are in step.

Run from the project root:
    python scripts/migrate_persistent_categories.py

This writes to whichever database Config points at (the live Aiven MySQL when
.env is set). Take a backup first with scripts/backup_db.py.
"""

import os
import sys

import mysql.connector

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402

UNGROUPED_CATEGORY = "未分组单词"

PROCEDURE_SQL = """
CREATE PROCEDURE update_category_counts()
BEGIN
    INSERT IGNORE INTO categories (name, word_count, last_updated)
    SELECT category, 0, MAX(updated_at)
    FROM words
    GROUP BY category;

    UPDATE categories c
    LEFT JOIN (
        SELECT category, COUNT(*) AS word_count, MAX(updated_at) AS last_updated
        FROM words
        GROUP BY category
    ) s ON s.category = c.name
    SET c.word_count = COALESCE(s.word_count, 0),
        c.last_updated = COALESCE(s.last_updated, c.last_updated);
END
"""


def migrate():
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )
    try:
        cursor = conn.cursor()

        cursor.execute(
            "INSERT IGNORE INTO categories (name, word_count) VALUES (%s, 0)",
            (UNGROUPED_CATEGORY,),
        )
        print(f'Ensured category "{UNGROUPED_CATEGORY}" exists')

        cursor.execute("DROP PROCEDURE IF EXISTS update_category_counts")
        cursor.execute(PROCEDURE_SQL)
        print("Replaced update_category_counts() with the non-truncating version")

        cursor.callproc("update_category_counts")
        for result in cursor.stored_results():
            result.fetchall()
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM categories")
        total = cursor.fetchone()[0]
        print(f"Done. {total} categories in the categories table")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
