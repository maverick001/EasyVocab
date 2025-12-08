import os
import shutil

def update_xml_tags():
    base_dir = r'c:\Users\bbcba\Downloads\BKDict\data'
    
    # Define replacements
    replacements = {
        '<tags>电信_计算机</tags>': '<tags>电信_IT</tags>',
        '<tags>心理学</tags>': '<tags>哲学_心理</tags>',
        '<tags>AI</tags>': '<tags>AI_CS</tags>'
    }

    # Files to process
    files_to_process = [
        'vocab.xml',
        'AI.xml',
        '经济_管理.xml',
        '日常词汇.xml',
        '人物.xml'
    ]

    print("Starting XML tag updates...")

    for i, filename in enumerate(files_to_process):
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            # Try checking if it's already renamed (special case for AI.xml)
            if filename == 'AI.xml':
                 filepath_renamed = os.path.join(base_dir, 'AI_CS.xml')
                 if os.path.exists(filepath_renamed):
                     print(f"File {i+1} (AI_CS.xml) found (already renamed). Processing...")
                     filepath = filepath_renamed
                     filename = 'AI_CS.xml' # Update filename for logging
                 else:
                     print(f"Skipping file {i+1} (not found)")
                     continue
            else:
                print(f"Skipping file {i+1} (not found)")
                continue
            
        print(f"Processing file {i+1}...")
        
        # Use a temporary file for writing
        temp_filepath = filepath + '.tmp'
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f_in, \
                 open(temp_filepath, 'w', encoding='utf-8') as f_out:
                 
                 for line in f_in:
                     for old_tag, new_tag in replacements.items():
                         if old_tag in line:
                             line = line.replace(old_tag, new_tag)
                     f_out.write(line)
            
            # Replace original file with modified temp file
            os.replace(temp_filepath, filepath)
            print(f"  - Updated file {i+1}")
            
        except Exception as e:
            print(f"  - Error processing file {i+1}: {e}")
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)

    # Rename AI.xml to AI_CS.xml
    old_ai_path = os.path.join(base_dir, 'AI.xml')
    new_ai_path = os.path.join(base_dir, 'AI_CS.xml')
    
    if os.path.exists(old_ai_path):
        try:
            os.rename(old_ai_path, new_ai_path)
            print(f"Renamed AI.xml to AI_CS.xml")
        except Exception as e:
            print(f"Error renaming AI.xml: {e}")
    else:
        if os.path.exists(new_ai_path):
             print("AI.xml already appears to be renamed to AI_CS.xml")
        else:
             print("AI.xml not found for renaming (check manual verification)")

    print("\nXML update process completed.")

if __name__ == "__main__":
    update_xml_tags()
