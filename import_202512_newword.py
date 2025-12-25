"""
Import 202512_NewWord.xml into category '202512_New'
All words are imported into the new category, preserving existing records elsewhere.
"""

import xml.etree.ElementTree as ET
import mysql.connector
from config import Config
import os
import sys
from datetime import datetime


def parse_xml_words(xml_file):
    """
    Parse words from XML file, extracting word and translation only.
    Category will be overridden to '202512_New'.
    """
    print(f"[*] Parsing XML file: {xml_file}")
    
    with open(xml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    root = ET.fromstring(content)
    words = []
    
    for item in root.findall('item'):
        word_elem = item.find('word')
        trans_elem = item.find('trans')
        
        if word_elem is not None and trans_elem is not None:
            word = word_elem.text.strip() if word_elem.text else ''
            translation = ''.join(trans_elem.itertext()).strip() if trans_elem.text else ''
            
            if word and translation:
                words.append({
                    'word': word,
                    'translation': translation
                })
    
    print(f"[OK] Found {len(words)} words in XML")
    return words


def import_words(words, conn):
    """
    Import words into database with category '202512_New'.
    All words get today's date as created_at.
    """
    cursor = conn.cursor()
    
    # Target category for all imports
    category = '202512_New'
    
    # Get current count for this category
    cursor.execute("SELECT COUNT(*) FROM words WHERE category = %s", (category,))
    before_count = cursor.fetchone()[0]
    
    # Insert SQL - uses INSERT IGNORE to skip exact duplicates (same word+category)
    insert_sql = """
        INSERT IGNORE INTO words (word, translation, category, example_sentence, created_at, updated_at)
        VALUES (%s, %s, %s, NULL, NOW(), NOW())
    """
    
    added = 0
    errors = 0
    
    for word_data in words:
        try:
            cursor.execute(insert_sql, (
                word_data['word'],
                word_data['translation'],
                category
            ))
            if cursor.rowcount > 0:
                added += 1
        except Exception as e:
            errors += 1
            print(f"[!] Error inserting '{word_data['word']}': {e}")
    
    conn.commit()
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM words WHERE category = %s", (category,))
    after_count = cursor.fetchone()[0]
    
    # Update category counts
    try:
        cursor.callproc('update_category_counts')
        conn.commit()
    except Exception as e:
        print(f"[!] Could not update category counts: {e}")
    
    cursor.close()
    
    return {
        'total_in_xml': len(words),
        'added': added,
        'skipped': len(words) - added,
        'errors': errors,
        'category_count': after_count
    }


def main():
    print("\n" + "="*60)
    print("  BKDict - Import 202512_NewWord.xml")
    print("  Target Category: 202512_New")
    print("="*60 + "\n")
    
    # XML file path
    xml_file = r'c:\Users\bbcba\Downloads\BKDict\data\202512_NewWord.xml'
    
    if not os.path.exists(xml_file):
        print(f"[X] Error: File not found: {xml_file}")
        sys.exit(1)
    
    # Parse XML
    words = parse_xml_words(xml_file)
    
    if not words:
        print("[X] No words found in XML file")
        sys.exit(1)
    
    # Connect to database
    print("\n[*] Connecting to database...")
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        print("[OK] Connected\n")
    except Exception as e:
        print(f"[X] Database connection failed: {e}")
        sys.exit(1)
    
    # Import words
    print("[*] Importing words to category '202512_New'...")
    stats = import_words(words, conn)
    conn.close()
    
    # Results
    print("\n" + "="*60)
    print("[OK] Import Complete!")
    print("="*60)
    print(f"Words in XML:           {stats['total_in_xml']}")
    print(f"Words added:            {stats['added']}")
    print(f"Skipped (duplicates):   {stats['skipped']}")
    print(f"Errors:                 {stats['errors']}")
    print(f"Total in '202512_New':  {stats['category_count']}")
    print("="*60 + "\n")
    
    if stats['category_count'] == stats['total_in_xml']:
        print("[SUCCESS] Category count matches XML word count.")
    else:
        print(f"[NOTE] Category has {stats['category_count']} words, XML had {stats['total_in_xml']}")


if __name__ == '__main__':
    main()
