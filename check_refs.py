import os

def check_file(filepath):
    print(f"Checking {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines):
        if 'sample_sentence' in line:
            print(f"Line {i+1}: {line.strip()}")
            found = True
            
    if not found:
        print(f"No 'sample_sentence' found in {filepath}")

if __name__ == "__main__":
    check_file('app.py')
