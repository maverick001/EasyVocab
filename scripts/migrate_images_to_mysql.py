"""
One-off migration: copy word images from static/images/word_images/ into the
word_images MySQL table, so Vercel and localhost serve the same images.

Safe by default: without --apply it only reads and reports. With --apply it
creates the word_images table if needed and inserts the images. It never
changes the words table and never touches the local files, so the rollback is
simply `DROP TABLE word_images` (the local files are still there).

Only images that a word references (image_file / image_file_2) are migrated.
Files no word points at are reported and left on disk.

Usage (from the project root):
    python scripts/migrate_images_to_mysql.py            # dry run
    python scripts/migrate_images_to_mysql.py --apply    # write to the database
"""

import argparse
import hashlib
import os
import sys

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import Config  # noqa: E402  (loads .env)
from utils.word_images import CREATE_WORD_IMAGES_TABLE_SQL  # noqa: E402

IMAGE_DIR = os.path.join(ROOT, "static", "images", "word_images")
MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MEDIUMBLOB_MAX = 16 * 1024 * 1024 - 1


def connect():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )


def referenced_filenames(cursor):
    cursor.execute(
        "SELECT image_file FROM words WHERE image_file IS NOT NULL AND image_file != '' "
        "UNION SELECT image_file_2 FROM words "
        "WHERE image_file_2 IS NOT NULL AND image_file_2 != ''"
    )
    return {row[0] for row in cursor.fetchall()}


def table_exists(cursor):
    cursor.execute("SHOW TABLES LIKE 'word_images'")
    return bool(cursor.fetchall())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply", action="store_true", help="write to the database (default: dry run)"
    )
    args = parser.parse_args()

    on_disk = set(os.listdir(IMAGE_DIR)) if os.path.isdir(IMAGE_DIR) else set()

    conn = connect()
    cursor = conn.cursor()
    referenced = referenced_filenames(cursor)
    exists = table_exists(cursor)

    stored = {}  # filename -> sha256 of what the table already holds
    if exists:
        cursor.execute("SELECT filename, SHA2(data, 256) FROM word_images")
        stored = {name: digest for name, digest in cursor.fetchall()}

    to_insert, already, conflicts, missing, too_big = [], [], [], [], []
    for name in sorted(referenced):
        path = os.path.join(IMAGE_DIR, name)
        if name not in on_disk:
            missing.append(name)
            continue
        with open(path, "rb") as f:
            data = f.read()
        if len(data) > MEDIUMBLOB_MAX:
            too_big.append(name)
            continue
        digest = hashlib.sha256(data).hexdigest()
        if name in stored:
            (already if stored[name] == digest else conflicts).append(name)
        else:
            to_insert.append((name, data, digest))

    orphans = sorted(on_disk - referenced)
    total = sum(len(d) for _, d, _ in to_insert)

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN (no changes)'}")
    print(f"word_images table exists: {exists}")
    print(f"Files on disk:                        {len(on_disk)}")
    print(f"Filenames referenced by words:        {len(referenced)}")
    print(f"  to insert:                          {len(to_insert)} ({total / 1048576:.1f} MB)")
    print(f"  already in table, identical:        {len(already)}")
    print(f"  in table but DIFFERENT bytes:       {len(conflicts)}")
    print(f"  referenced but missing on disk:     {len(missing)}")
    print(f"  too large for MEDIUMBLOB:           {len(too_big)}")
    print(f"Unreferenced files left on disk:      {len(orphans)}")
    for label, names in (("conflict", conflicts), ("missing", missing), ("too big", too_big)):
        for name in names:
            print(f"  {label}: {name}")

    if conflicts or too_big:
        print("Stopping: resolve the conflicts above first.")
        conn.close()
        return 1

    if not args.apply:
        print("Dry run only. Re-run with --apply to write.")
        conn.close()
        return 0

    cursor.execute(CREATE_WORD_IMAGES_TABLE_SQL)
    for name, data, _ in to_insert:
        ext = os.path.splitext(name)[1].lower()
        cursor.execute(
            "INSERT INTO word_images (filename, mime_type, data) VALUES (%s, %s, %s)",
            (name, MIME_BY_EXTENSION.get(ext, "image/jpeg"), data),
        )
    conn.commit()

    # Verify from the database side: same length and SHA-256 as the local file.
    bad = []
    for name, data, digest in to_insert:
        cursor.execute(
            "SELECT LENGTH(data), SHA2(data, 256) FROM word_images WHERE filename = %s",
            (name,),
        )
        row = cursor.fetchone()
        if row is None or row[0] != len(data) or row[1] != digest:
            bad.append(name)

    cursor.execute("SELECT COUNT(*) FROM word_images")
    print(f"Inserted {len(to_insert)}; table now holds {cursor.fetchone()[0]} rows.")
    conn.close()

    if bad:
        print(f"VERIFICATION FAILED for {len(bad)} file(s):")
        for name in bad:
            print(f"  {name}")
        return 1
    print("Verified: every inserted image matches its local file (size and SHA-256).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
