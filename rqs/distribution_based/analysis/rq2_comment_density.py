#!/usr/bin/env python3
import json
import os
import sys
from collections import defaultdict

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read().lstrip()
    if text.startswith('['):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def iter_ccps(data):
    seen = set()
    for item in data:
        key = (item.get('SDK'), str(item.get('id', '')).split('-', 1)[0])
        if key in seen:
            continue
        seen.add(key)
        yield item

def line_count(line_range):
    if isinstance(line_range, (list, tuple)) and len(line_range) >= 2:
        return max(line_range[1] - line_range[0] + 1, 0)
    return 0

def code_key(record):
    dir_path = '/'.join(record.get('dirPath', []))
    code_line = record.get('code_line', [])
    if len(code_line) >= 2:
        return f'{dir_path}:{code_line[0]}-{code_line[1]}'
    return f'{dir_path}:unknown'

def main():
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'rqs/distribution_based/results/rq2_comment_density.json'
    records = load_data(data_file)
    entity_stats = defaultdict(lambda: {'comment_lines': 0, 'code_lines': 0})
    seen_code = set()
    for item in iter_ccps(records):
        entity = item.get('code_entity_type', 'unknown')
        entity_stats[entity]['comment_lines'] += line_count(item.get('comment_line', []))
        ck = code_key(item)
        if ck not in seen_code:
            seen_code.add(ck)
            entity_stats[entity]['code_lines'] += line_count(item.get('code_line', []))
    results = {}
    for entity, stats in entity_stats.items():
        code_lines = stats['code_lines']
        comment_lines = stats['comment_lines']
        results[entity] = {
            'comment_line_count': comment_lines,
            'code_line_count': code_lines,
            'comment_density': round(comment_lines / code_lines, 4) if code_lines else 0.0,
        }
    total_comments = sum(v['comment_line_count'] for v in results.values())
    total_code = sum(v['code_line_count'] for v in results.values())
    results['total'] = {
        'comment_line_count': total_comments,
        'code_line_count': total_code,
        'comment_density': round(total_comments / total_code, 4) if total_code else 0.0,
    }
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'RQ2 saved to {output_file}: overall density {results["total"]["comment_density"]}')

if __name__ == '__main__':
    main()
