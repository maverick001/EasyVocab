"""
Import Raw XML Script
Cleans raw XML files (removes extra fields) and imports them into the database
"""

import xml.etree.ElementTree as ET
import mysql.connector
from config import Config
from utils import parse_and_import_xml
import os
import sys


def clean_raw_xml(input_file, output_file):
    """
    Clean raw XML vocabulary file by keeping only word, trans, and tags fields

    Args:
        input_file: Path to raw XML file
        output_file: Path to save cleaned XML file

    Returns:
        Number of items processed
    """
    print(f"📖 Reading raw XML file: {input_file}")

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the XML
    tree = ET.fromstring(content)

    # Create the output XML structure
    output_lines = ['<wordbook>']

    # Process each item
    items_count = 0
    for item in tree.findall('item'):
        word = item.find('word')
        trans = item.find('trans')
        tags = item.find('tags')

        if word is not None and trans is not None:
            # Start item tag
            output_lines.append('<item>')

            # Add word
            word_text = word.text.strip() if word.text else ''
            output_lines.append(f'  <word>{word_text}</word>')

            # Add trans (preserve CDATA)
            trans_text = trans.text.strip() if trans.text else ''
            output_lines.append(f'  <trans><![CDATA[{trans_text}]]></trans>')

            # Add tags if present
            if tags is not None and tags.text:
                tags_text = tags.text.strip()
                output_lines.append(f'  <tags>{tags_text}</tags>')

            # Close item tag
            output_lines.append('</item>')
            items_count += 1

    # Close wordbook tag
    output_lines.append('</wordbook>')

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"✅ Cleaned XML saved to: {output_file}")
    print(f"📊 Total items processed: {items_count}")

    return items_count


def import_cleaned_xml(cleaned_file):
    """
    Import cleaned XML file into database

    Args:
        cleaned_file: Path to cleaned XML file
    """
    print(f"\n🔄 Importing to database...")

    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )

        # Import the cleaned XML
        stats = parse_and_import_xml(cleaned_file, conn, batch_size=1000)

        # Close connection
        conn.close()

        # Print results
        print(f"\n{'='*60}")
        print(f"✅ Import completed successfully!")
        print(f"{'='*60}")
        print(f"📝 Total processed:      {stats['total_processed']}")
        print(f"✅ Words added:          {stats['added']}")
        print(f"⏭️  Duplicates skipped:   {stats['skipped_duplicates']}")
        print(f"❌ Errors:               {stats['errors']}")
        print(f"{'='*60}\n")

        return stats

    except Exception as e:
        print(f"❌ Error during import: {str(e)}")
        return None


def main():
    """Main function"""
    print("\n" + "="*60)
    print("  BKDict - Raw XML Cleaner and Importer")
    print("="*60 + "\n")

    # Define file paths
    input_file = r'c:\Users\bbcba\Downloads\BKDict\data\AI.xml'
    output_file = r'c:\Users\bbcba\Downloads\BKDict\data\AI_cleaned.xml'

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)

    # Step 1: Clean the raw XML
    try:
        clean_raw_xml(input_file, output_file)
    except Exception as e:
        print(f"❌ Error during cleaning: {str(e)}")
        sys.exit(1)

    # Step 2: Import the cleaned XML
    stats = import_cleaned_xml(output_file)

    if stats and stats['added'] > 0:
        print("🎉 All done! You can now browse the AI vocabulary in the web app.")

    # Optional: Remove the temporary cleaned file
    # os.remove(output_file)


if __name__ == '__main__':
    main()
