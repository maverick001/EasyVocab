"""
Tag words that have no "n./v./adj." prefix with their word type, using Gemini.

The quiz keeps its four options the same type (all adjectives, all nouns ...).
A word's type is read from its translation prefix; words without a prefix need
Gemini once, and the answer is cached in words.ai_pos. The quiz tags a word the
first time it asks about it, so this script is optional: run it to tag the rest
in one go, which also makes those words eligible as wrong options.

Safe by default: without --apply it only reads and reports (no Gemini calls, no
writes). With --apply it adds the ai_pos column if it is missing, then asks
Gemini in batches and saves each batch as it goes. Only ai_pos changes. It is
safe to stop and rerun: words already tagged are skipped. Rollback:
    UPDATE words SET ai_pos = NULL;

Every Gemini call counts toward your API quota (about 1 call per --batch-size
words), so try a small --limit first.

Usage (from the project root):
    python scripts/tag_word_types.py                       # dry run, counts only
    python scripts/tag_word_types.py --apply --limit 200   # tag 200 words
    python scripts/tag_word_types.py --apply               # tag everything left
"""

import argparse
import os
import sys

import mysql.connector
from openai import BadRequestError, OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import Config  # noqa: E402  (loads .env)
from utils.word_types import (  # noqa: E402
    build_batch_prompt,
    join_ai_pos,
    parse_batch_reply,
    parse_word_types,
)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def connect():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
    )


def column_exists(cursor):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'words' AND COLUMN_NAME = 'ai_pos'",
        (Config.DB_NAME,),
    )
    return cursor.fetchone()[0] > 0


def pending_words(cursor, has_column):
    """[(id, word, translation)] with no prefix and no cached answer, one per word."""
    condition = "WHERE ai_pos IS NULL" if has_column else ""
    cursor.execute(f"SELECT id, word, translation FROM words {condition} ORDER BY id")
    seen = set()
    pending = []
    total = 0
    with_prefix = 0
    for word_id, word, translation in cursor.fetchall():
        total += 1
        if parse_word_types(translation):
            with_prefix += 1
            continue
        key = (word, translation)
        if key not in seen:  # rows in several categories share one translation
            seen.add(key)
            pending.append((word_id, word, translation))
    return pending, total, with_prefix


def ask_gemini(client, prompt):
    kwargs = {
        "model": Config.GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    if Config.GEMINI_REASONING_EFFORT:
        try:
            return client.chat.completions.create(
                reasoning_effort=Config.GEMINI_REASONING_EFFORT, **kwargs
            )
        except BadRequestError:
            pass  # the model does not support this setting; use its default
    return client.chat.completions.create(**kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply", action="store_true", help="call Gemini and write ai_pos (default: dry run)"
    )
    parser.add_argument("--limit", type=int, help="tag at most this many words this run")
    parser.add_argument("--batch-size", type=int, default=40, help="words per Gemini call")
    args = parser.parse_args()

    connection = connect()
    cursor = connection.cursor()
    has_column = column_exists(cursor)
    pending, total, with_prefix = pending_words(cursor, has_column)
    if args.limit:
        pending = pending[: args.limit]
    calls = -(-len(pending) // args.batch_size)

    print(f"Words in the table (not yet tagged): {total}")
    print(f"  type read from the translation prefix: {with_prefix}")
    print(f"  need Gemini (this run): {len(pending)} -> about {calls} Gemini calls")

    if not args.apply:
        print("\nDry run: nothing was changed. Rerun with --apply to tag them.")
        connection.close()
        return
    if not Config.GEMINI_API_KEY:
        sys.exit("GOOGLE_API_KEY is not set in .env")

    if not has_column:
        print("Adding the ai_pos column...")
        cursor.execute("ALTER TABLE words ADD COLUMN ai_pos VARCHAR(50) DEFAULT NULL")
        connection.commit()

    client = OpenAI(api_key=Config.GEMINI_API_KEY, base_url=GEMINI_URL)
    tagged = skipped = 0
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        by_id = {word_id: (word, translation) for word_id, word, translation in batch}
        try:
            response = ask_gemini(client, build_batch_prompt(batch))
            reply = response.choices[0].message.content if response.choices else ""
        except Exception as err:  # keep going: the next run retries what is left
            print(f"  batch at {start}: Gemini failed ({err}); skipped")
            skipped += len(batch)
            continue

        answers = parse_batch_reply(reply)
        for word_id, types in answers.items():
            if word_id not in by_id:
                continue
            word, translation = by_id[word_id]
            cursor.execute(
                "UPDATE words SET ai_pos = %s WHERE word = %s AND translation = %s",
                (join_ai_pos(types), word, translation),
            )
            tagged += 1
        connection.commit()
        skipped += len(batch) - len([i for i in answers if i in by_id])
        print(f"  {min(start + len(batch), len(pending))}/{len(pending)} done")

    connection.close()
    print(f"\nTagged {tagged} words; {skipped} got no usable answer (rerun to retry them).")


if __name__ == "__main__":
    main()
