"""
Import Full Vocabulary XML File
Imports the complete vocab.xml file with 30,000+ words into the database
"""

import xml.etree.ElementTree as ET
import mysql.connector
from config import Config
from utils import parse_and_import_xml
import os
import sys
import time


def main():
    """Main function to import vocab.xml"""
    print("\n" + "="*70)
    print("  BKDict - Full Vocabulary Importer")
    print("  Importing 30,000+ words from vocab.xml")
    print("="*70 + "\n")

    # Define file path - MODIFY THIS to point to your vocab.xml
    vocab_file = r'c:\Users\bbcba\Downloads\BKDict\data\vocab.xml'

    # Check if file exists
    if not os.path.exists(vocab_file):
        print(f"❌ Error: Vocabulary file not found!")
        print(f"   Expected location: {vocab_file}")
        print(f"\n📝 Please update the vocab_file path in this script to point to your vocab.xml")
        print(f"   Edit line 19 in: {__file__}")
        sys.exit(1)

    # Get file size for progress estimation
    file_size_mb = os.path.getsize(vocab_file) / (1024 * 1024)
    print(f"📄 File found: {vocab_file}")
    print(f"📊 File size: {file_size_mb:.2f} MB")
    print(f"\n⏱️  Estimated import time: {int(file_size_mb * 0.5)} - {int(file_size_mb * 1)} minutes")
    print(f"    (depending on your system performance)\n")

    # Confirm before proceeding
    print("⚠️  IMPORTANT REMINDERS:")
    print("   1. Close the Flask app if it's running")
    print("   2. Existing words will NOT be overwritten")
    print("   3. Only new words will be added")
    print("   4. Your sample sentences and edits are safe\n")

    response = input("📋 Ready to import? Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("❌ Import cancelled.")
        sys.exit(0)

    # Start import
    print(f"\n{'='*70}")
    print("🚀 Starting import process...")
    print(f"{'='*70}\n")

    start_time = time.time()

    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        print("✅ Database connected\n")

        # Get initial word count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM words")
        initial_count = cursor.fetchone()[0]
        cursor.close()

        print(f"📊 Words in database before import: {initial_count:,}\n")

        # Import the vocabulary file
        print("📖 Parsing XML and importing to database...")
        print("    (This may take several minutes for large files)\n")

        stats = parse_and_import_xml(vocab_file, conn, batch_size=1000)

        # Get final word count
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM words")
        final_count = cursor.fetchone()[0]
        cursor.close()

        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        # Print results
        print(f"\n{'='*70}")
        print("✅ Import completed successfully!")
        print(f"{'='*70}")
        print(f"⏱️  Time elapsed:           {minutes}m {seconds}s")
        print(f"📝 Total processed:         {stats['total_processed']:,} words")
        print(f"✅ New words added:         {stats['added']:,}")
        print(f"⏭️  Duplicates skipped:     {stats['skipped_duplicates']:,}")
        print(f"❌ Errors:                  {stats['errors']:,}")
        print(f"📊 Total words now:         {final_count:,}")
        print(f"📈 Database growth:         +{final_count - initial_count:,} words")
        print(f"{'='*70}\n")

        # Show category breakdown
        cursor = conn.cursor()
        cursor.execute("SELECT category, COUNT(*) as count FROM words GROUP BY category ORDER BY count DESC")
        categories = cursor.fetchall()
        cursor.close()

        # Close connection (moved here after all queries are done)
        conn.close()

        print("📂 Words by Category:")
        print(f"{'─'*70}")
        for cat, count in categories:
            print(f"   {cat:<30} {count:>6,} words")
        print(f"{'─'*70}")
        print(f"   {'TOTAL':<30} {final_count:>6,} words")
        print(f"{'='*70}\n")

        print("🎉 All done! You can now:")
        print("   1. Start the Flask app: python app.py")
        print("   2. Open http://localhost:5000 in your browser")
        print("   3. Select a category and start learning!")
        print()

    except Exception as e:
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print(f"\n{'='*70}")
        print("❌ Import failed!")
        print(f"{'='*70}")
        print(f"⏱️  Time before failure: {minutes}m {seconds}s")
        print(f"❌ Error: {str(e)}")
        print(f"{'='*70}\n")
        print("💡 Troubleshooting:")
        print("   1. Check if MySQL is running")
        print("   2. Verify .env file has correct database credentials")
        print("   3. Ensure vocab.xml file path is correct")
        print("   4. Check if the XML file is valid BKDict format")
        print()
        sys.exit(1)


if __name__ == '__main__':
    main()
