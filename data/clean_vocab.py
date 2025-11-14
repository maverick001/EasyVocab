import re
import xml.etree.ElementTree as ET

def clean_xml(input_file, output_file):
    """Clean XML vocabulary file by keeping only word, trans, and tags fields."""

    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the XML
    tree = ET.fromstring(content)

    # Create the output XML structure
    output_lines = ['<wordbook>']

    # Process each item
    for item in tree.findall('item'):
        word = item.find('word')
        trans = item.find('trans')
        tags = item.find('tags')

        if word is not None and trans is not None:
            # Start item tag
            output_lines.append('<item>')

            # Add word (capitalize first letter if it's a proper noun or name)
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

    # Close wordbook tag
    output_lines.append('</wordbook>')

    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"Cleaned XML saved to: {output_file}")
    print(f"Total items processed: {len(tree.findall('item'))}")

if __name__ == '__main__':
    input_file = r'c:\Users\bbcba\Downloads\BKDict\data\文化.xml'
    output_file = r'c:\Users\bbcba\Downloads\BKDict\data\文化_cleaned.xml'

    clean_xml(input_file, output_file)
