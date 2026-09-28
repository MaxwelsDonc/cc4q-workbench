#!/usr/bin/env python3
import json
import os
import sys
from collections import Counter

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

def main():
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'rqs/distribution_based/results/rq1_distribution.json'
    records = load_data(data_file)
    ccps = list(iter_ccps(records))
    allocated = {}
    for item in records:
        sdk = item.get('SDK')
        try:
            ccp_id = int(str(item.get('id', '')).split('-', 1)[0])
        except ValueError:
            continue
        allocated[sdk] = max(allocated.get(sdk, 0), ccp_id)
    combination_counts = Counter()
    for item in ccps:
        key = (item.get('code_entity_type', 'unknown'), item.get('comment_type', 'unknown'))
        combination_counts[key] += 1
    total_present = len(ccps)
    combination_distribution = {}
    for (entity, form), count in combination_counts.items():
        combination_distribution[f'{entity}+{form}'] = {
            'code_entity': entity,
            'comment_forms': form,
            'count': count,
            'percentage': round(count / total_present * 100, 2),
        }
    results = {
        'combination_distribution': combination_distribution,
        'total_ccps_with_units': total_present,
        'allocated_ccp_ids_per_sdk': allocated,
        'allocated_ccp_ids_total': sum(allocated.values()),
    }
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'RQ1 saved to {output_file}: {total_present} CCPs present '
          f'(of {sum(allocated.values())} allocated ids)')

if __name__ == '__main__':
    main()
