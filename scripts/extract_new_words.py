import sys
import os
import argparse
import xml.etree.ElementTree as ET
import mysql.connector
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def get_db_connection():
    load_dotenv()
    
    host = os.environ.get('DB_HOST')
    port = int(os.environ.get('DB_PORT', 3306))
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    database = os.environ.get('DB_NAME')
    
    if not all([host, user, password, database]):
        raise ValueError("Missing database credentials in .env file.")
        
    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )

def parse_xml(xml_path, override_category=None):
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"XML file not found: {xml_path}")
        
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    words = []
    
    # We assume the structure is <wordbook><item>...</item></wordbook>
    for item in root.findall('.//item'):
        word_text = item.findtext('word')
        translation = item.findtext('trans')
        tags = item.findtext('tags')
        
        if not word_text or not translation:
            continue
            
        category = override_category if override_category else (tags if tags else "Uncategorized")
        
        words.append({
            'word': word_text.strip(),
            'translation': translation.strip(),
            'category': category.strip()
        })
        
    return words

def main():
    parser = argparse.ArgumentParser(description="Extract new vocabulary from XML and upload to Aiven DB.")
    parser.add_argument("xml_file", help="Path to the XML file (e.g., ./data/202512_NewWord.xml)")
    parser.add_argument("--category", help="Override the category/tag for all extracted words", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Parse the XML and print the results without modifying the database")
    
    args = parser.parse_args()
    
    print(f"Parsing XML file: {args.xml_file}")
    words = parse_xml(args.xml_file, args.category)
    
    print(f"Extracted {len(words)} words.")
    
    if not words:
        print("No words found in the XML file.")
        return

    # To group by category implicitly
    categories_found = set(w['category'] for w in words)
    print(f"Categories to update: {', '.join(categories_found)}")
    
    if args.dry_run:
        print("\n--- DRY RUN ---")
        print("First 5 words that would be inserted:")
        for w in words[:5]:
            print(f" - {w['word']}: {w['translation'][:30]}... [{w['category']}]")
        print("\nSkipping database insertion due to --dry-run flag.")
        return
        
    print("\nConnecting to database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Create categories if they don't exist
        for cat in categories_found:
            cursor.execute(
                "INSERT IGNORE INTO categories (name, word_count) VALUES (%s, 0)",
                (cat,)
            )
        
        # Get all existing words from the database
        cursor.execute("SELECT DISTINCT word FROM words")
        existing_words = {row[0] for row in cursor.fetchall()}
        
        # 2. Insert words (only those that don't already exist globally)
        batch_size = 1000
        total_inserted = 0
        skipped_count = 0
        
        insert_query = """
        INSERT IGNORE INTO words (word, translation, category) 
        VALUES (%s, %s, %s)
        """
        
        word_data = []
        for w in words:
            if w['word'] not in existing_words:
                word_data.append((w['word'], w['translation'], w['category']))
                existing_words.add(w['word'])  # add to our local set to prevent duplicates within the XML file itself
            else:
                skipped_count += 1
                
        print(f"Skipped {skipped_count} words that already exist in the database.")
        
        for i in range(0, len(word_data), batch_size):
            batch = word_data[i:i + batch_size]
            cursor.executemany(insert_query, batch)
            total_inserted += cursor.rowcount
            conn.commit()
            print(f"Inserted batch of {len(batch)} words. New additions: {cursor.rowcount}")
            
        # 3. Update category counts via stored procedure
        print("Updating category statistics...")
        cursor.execute("CALL update_category_counts()")
        conn.commit()
        
        print(f"\nUpload complete! Successfully added {total_inserted} new words.")
        
    except Exception as e:
        print(f"Error during database operation: {e}")
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    main()
