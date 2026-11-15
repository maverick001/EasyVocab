"""
Back up the BKDict database to the gitignored backups/ folder.

Read-only: it runs SELECTs and never changes the database.

Each run writes two things, named with the same timestamp:
    backups/bkdict_backup_<timestamp>.json     every table's rows
    backups/bkdict_backup_<timestamp>_images/  one file per stored word image

The image bytes live only in the word_images table, so they are written as
ordinary image files next to the JSON; the JSON keeps each image's filename,
MIME type and size. A table that does not exist is reported and skipped.

Usage (from the project root):
    python scripts/backup_db.py
"""

import base64
import datetime
import decimal
import json
import os
import sys

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import Config  # noqa: E402  (loads .env)

BACKUP_DIR = os.path.join(ROOT, "backups")

# Tables saved row by row into the JSON file. category_stats is a view; it is
# kept because earlier backups included it.
ROW_TABLES = (
    "words",
    "word_history",
    "categories",
    "daily_study_log",
    "daily_word_reviews",
    "category_stats",
)

# Saved separately: metadata in the JSON, bytes as files.
IMAGE_TABLE = "word_images"

# MySQL error number for "table doesn't exist"
ER_NO_SUCH_TABLE = 1146


def serialize_value(value):
    """
    Convert one database value into something json.dump accepts.

    Args:
        value: a value as returned by mysql-connector

    Returns:
        The value unchanged, or a JSON-friendly equivalent
    """
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, datetime.timedelta):
        return value.total_seconds()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        # Text from a binary-collated column comes back as bytes
        try:
            return bytes(value).decode("utf-8")
        except UnicodeDecodeError:
            return {"base64": base64.b64encode(bytes(value)).decode("ascii")}
    return value


def serialize_row(row):
    """Convert one row (a dict of column to value) for JSON"""
    return {key: serialize_value(value) for key, value in row.items()}


def safe_image_name(filename):
    """
    File name to store an image under, with any folder part removed.

    Stored names look like img_12_1_1700000000.jpg, but the value comes from
    the database, so it must never be able to write outside the images folder.

    Returns:
        A bare file name, or None if nothing usable is left
    """
    name = os.path.basename((filename or "").replace("\\", "/"))
    return name if name not in ("", ".", "..") else None


def backup_rows(cursor, table):
    """
    Read every row of a table.

    Returns:
        A list of JSON-ready rows, or None if the table does not exist
    """
    try:
        cursor.execute(f"SELECT * FROM `{table}`")
    except mysql.connector.Error as err:
        if err.errno == ER_NO_SUCH_TABLE:
            return None
        raise
    return [serialize_row(row) for row in cursor.fetchall()]


def backup_images(conn, images_dir):
    """
    Write every stored image to images_dir and return its metadata.

    Images are read one at a time so the whole table is never held in memory.

    Returns:
        A list of {filename, mime_type, created_at, size, saved_as} dicts, or
        None if the word_images table does not exist
    """
    cursor = conn.cursor(dictionary=True)
    try:
        try:
            cursor.execute(
                f"SELECT filename, mime_type, created_at FROM `{IMAGE_TABLE}` "
                "ORDER BY filename"
            )
        except mysql.connector.Error as err:
            if err.errno == ER_NO_SUCH_TABLE:
                return None
            raise
        entries = [serialize_row(row) for row in cursor.fetchall()]

        if entries:
            os.makedirs(images_dir, exist_ok=True)

        for entry in entries:
            cursor.execute(
                f"SELECT data FROM `{IMAGE_TABLE}` WHERE filename = %s",
                (entry["filename"],),
            )
            row = cursor.fetchone()
            data = bytes(row["data"]) if row and row["data"] is not None else b""
            saved_as = safe_image_name(entry["filename"])
            entry["size"] = len(data)
            entry["saved_as"] = saved_as
            if saved_as:
                with open(os.path.join(images_dir, saved_as), "wb") as f:
                    f.write(data)
        return entries
    finally:
        cursor.close()


def backup_db():
    """
    Run the backup.

    Returns:
        True if the backup completed, False if it failed
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"bkdict_backup_{timestamp}.json")
    images_dir = os.path.join(BACKUP_DIR, f"bkdict_backup_{timestamp}_images")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"Starting backup to {backup_file}...")

    conn = None
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
        )
        cursor = conn.cursor(dictionary=True)

        backup_data = {}
        for table in ROW_TABLES:
            rows = backup_rows(cursor, table)
            if rows is None:
                print(f"  [SKIP] {table}: table not found")
                continue
            backup_data[table] = rows
            print(f"  {table}: {len(rows)} records")
        cursor.close()

        images = backup_images(conn, images_dir)
        if images is None:
            print(f"  [SKIP] {IMAGE_TABLE}: table not found")
        else:
            backup_data[IMAGE_TABLE] = images
            total_bytes = sum(image["size"] for image in images)
            print(
                f"  {IMAGE_TABLE}: {len(images)} images, "
                f"{total_bytes / (1024 * 1024):.1f} MB"
            )

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Backup completed: {backup_file}")
        if images:
            print(f"[OK] Images saved in: {images_dir}")
        return True

    except mysql.connector.Error as err:
        print(f"[ERROR] Database error: {err}")
        return False
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        return False
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    sys.exit(0 if backup_db() else 1)
