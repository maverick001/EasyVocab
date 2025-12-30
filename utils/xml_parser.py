"""
XML Parser for BKDict Vocabulary Import
Handles XML file validation, parsing, and batch database insertion
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple
import re


class XMLParserError(Exception):
    """Custom exception for XML parsing errors"""
    pass


class VocabularyXMLParser:
    """
    Parser for vocabulary XML files in BKDict format
    Expected format:
    <wordbook>
        <item>
            <word>example</word>
            <trans><![CDATA[translation text]]></trans>
            <tags>category</tags>
        </item>
    </wordbook>
    """

    def __init__(self, xml_file_path: str):
        """
        Initialize parser with XML file path

        Args:
            xml_file_path: Path to the XML file to parse
        """
        self.xml_file_path = xml_file_path
        self.tree = None
        self.root = None

    def validate_xml(self) -> Tuple[bool, str]:
        """
        Validate XML file format and structure

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse XML file
            self.tree = ET.parse(self.xml_file_path)
            self.root = self.tree.getroot()

            # Check root element
            if self.root.tag != 'wordbook':
                return False, f"Invalid root element: expected 'wordbook', got '{self.root.tag}'"

            # Check if there are any items
            items = self.root.findall('item')
            if not items:
                return False, "No word items found in XML file"

            # Validate first few items have required structure
            for i, item in enumerate(items[:5]):  # Check first 5 items
                word = item.find('word')
                trans = item.find('trans')
                tags = item.find('tags')

                if word is None:
                    return False, f"Item {i+1}: Missing 'word' element"
                if trans is None:
                    return False, f"Item {i+1}: Missing 'trans' element"
                if tags is None:
                    return False, f"Item {i+1}: Missing 'tags' element"

            return True, "XML validation successful"

        except ET.ParseError as e:
            return False, f"XML parsing error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def parse_words(self) -> List[Dict[str, str]]:
        """
        Parse all words from the XML file

        Returns:
            List of dictionaries containing word data:
            [{'word': str, 'translation': str, 'category': str}, ...]

        Raises:
            XMLParserError: If XML hasn't been validated or parsing fails
        """
        if self.root is None:
            raise XMLParserError("XML not validated. Call validate_xml() first.")

        words_data = []

        for item in self.root.findall('item'):
            try:
                # Extract word (required)
                word_elem = item.find('word')
                word = word_elem.text.strip() if word_elem is not None and word_elem.text else None

                # Extract translation from CDATA (required)
                trans_elem = item.find('trans')
                translation = self._extract_cdata_content(trans_elem)

                # Extract category/tag (required)
                tags_elem = item.find('tags')
                category = tags_elem.text.strip() if tags_elem is not None and tags_elem.text else None

                # Skip items with missing required fields
                if not word or not translation or not category:
                    continue

                words_data.append({
                    'word': word,
                    'translation': translation,
                    'category': category
                })

            except Exception as e:
                # Log error but continue parsing other items
                print(f"Warning: Error parsing item: {str(e)}")
                continue

        return words_data

    def _extract_cdata_content(self, element) -> str:
        """
        Extract text content from element, including CDATA sections

        Args:
            element: XML element that may contain CDATA

        Returns:
            Cleaned text content
        """
        if element is None:
            return ""

        # Get all text content (including CDATA)
        content = ''.join(element.itertext()).strip()

        # Remove extra whitespace while preserving line breaks
        content = re.sub(r'[ \t]+', ' ', content)  # Replace multiple spaces/tabs with single space
        content = re.sub(r'\n\s+', '\n', content)  # Clean up indented lines

        return content

    def import_to_database(self, db_connection, batch_size: int = 1000) -> Dict[str, int]:
        """
        Import parsed words to MySQL database with batch processing

        Args:
            db_connection: MySQL database connection object
            batch_size: Number of records to insert per batch (default: 1000)

        Returns:
            Dictionary with import statistics:
            {
                'total_processed': int,
                'added': int,
                'skipped_duplicates': int,
                'errors': int
            }
        """
        # Validate and parse XML
        is_valid, message = self.validate_xml()
        if not is_valid:
            raise XMLParserError(f"XML validation failed: {message}")

        words_data = self.parse_words()

        stats = {
            'total_processed': len(words_data),
            'added': 0,
            'skipped_duplicates': 0,
            'errors': 0
        }

        cursor = db_connection.cursor()

        # SQL for inserting words (ignore duplicates based on unique constraint)
        # On duplicate: update timestamp to mark it was seen, but keep existing data
        insert_sql = """
            INSERT INTO words (word, translation, category, example_sentence, review_count)
            VALUES (%s, %s, %s, NULL, 1)
            ON DUPLICATE KEY UPDATE updated_at=updated_at
        """

        # Process in batches for better performance
        for i in range(0, len(words_data), batch_size):
            batch = words_data[i:i + batch_size]
            batch_values = []

            for word_data in batch:
                batch_values.append((
                    word_data['word'],
                    word_data['translation'],
                    word_data['category']
                ))

            try:
                # Execute batch insert
                rows_before = self._get_word_count(cursor)
                cursor.executemany(insert_sql, batch_values)
                db_connection.commit()
                rows_after = self._get_word_count(cursor)

                # Calculate how many were actually added
                added_in_batch = rows_after - rows_before
                stats['added'] += added_in_batch
                stats['skipped_duplicates'] += len(batch) - added_in_batch

            except Exception as e:
                db_connection.rollback()
                stats['errors'] += len(batch)
                print(f"Error importing batch: {str(e)}")

        # Update category counts
        try:
            cursor.callproc('update_category_counts')
            db_connection.commit()
        except Exception as e:
            print(f"Warning: Could not update category counts: {str(e)}")

        cursor.close()
        return stats

    def _get_word_count(self, cursor) -> int:
        """
        Helper method to get current total word count

        Args:
            cursor: Database cursor

        Returns:
            Total number of words in database
        """
        cursor.execute("SELECT COUNT(*) FROM words")
        result = cursor.fetchone()
        return result[0] if result else 0


def parse_and_import_xml(xml_file_path: str, db_connection, batch_size: int = 1000) -> Dict[str, int]:
    """
    Convenience function to parse and import XML file in one call

    Args:
        xml_file_path: Path to XML file
        db_connection: MySQL database connection
        batch_size: Batch size for inserts (default: 1000)

    Returns:
        Dictionary with import statistics

    Raises:
        XMLParserError: If parsing or import fails
    """
    parser = VocabularyXMLParser(xml_file_path)
    return parser.import_to_database(db_connection, batch_size)
