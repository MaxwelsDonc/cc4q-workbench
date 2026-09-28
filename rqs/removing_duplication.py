import json
import argparse

def removing_duplication(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        data = json.load(f)
    seen = set()
    unique_data = []
    for item in data:
        if item not in seen:
            unique_data.append(item)
            seen.add(item)
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Return the json file without duplication')
    parser.add_argument('file', type=str, help='Input the file of the json file')
    args = parser.parse_args()
    file_dir = args.file
    removing_duplication(file_dir)
