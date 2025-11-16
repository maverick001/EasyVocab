"""
Script to fix all connection leaks in app.py by adding try-finally blocks
"""

import re

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Patterns to fix - we need to add `conn = None` before try and `finally: if conn: conn.close()` after except

# Fix for change_word_category (line ~377)
content = re.sub(
    r'(def change_word_category\(word_id\):.*?""")\s+(try:)',
    r'\1\n    conn = None\n    \2',
    content,
    flags=re.DOTALL
)

content = re.sub(
    r'(change_word_category.*?except Exception as e:.*?}), 500\)(.*?)(@app\.route)',
    r'\1, 500\n    finally:\n        if conn:\n            conn.close()\n\n\n\3',
    content,
    flags=re.DOTALL
)

# Fix for delete_word (line ~446)
content = re.sub(
    r'(def delete_word\(word_id\):.*?""")\s+(try:)',
    r'\1\n    conn = None\n    \2',
    content,
    flags=re.DOTALL
)

# Fix for increment_review_counter
content = re.sub(
    r'(def increment_review_counter\(word_id\):.*?""")\s+(try:)',
    r'\1\n    conn = None\n    \2',
    content,
    flags=re.DOTALL
)

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed connection leaks in app.py")
