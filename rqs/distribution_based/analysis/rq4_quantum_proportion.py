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

def main():
    data_file = sys.argv[1] if len(sys.argv) > 1 else 'data/final_data/CCPs_final_modified_r2_cleaned_validated.jsonl'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'rqs/distribution_based/results/rq4_quantum_proportion.json'
    records = load_data(data_file)
    total = Counter()
    quantum = Counter()
    for item in records:
        key = (item.get('code_entity_type', 'unknown'), item.get('comment_type', 'unknown'))
        total[key] += 1
        if item.get('is_quantum_specific'):
            quantum[key] += 1
    distribution = {}
    for (entity, form), count in total.items():
        q = quantum[(entity, form)]
        distribution[f'{entity}+{form}'] = {
            'code_entity': entity,
            'comment_forms': form,
            'total_count': count,
            'quantum_count': q,
            'quantum_percentage': round(q / count * 100, 4) if count else 0.0,
        }
    overall_total = sum(total.values())
    overall_quantum = sum(quantum.values())
    results = {
        'quantum_proportion_distribution': distribution,
        'overall': {
            'total_count': overall_total,
            'quantum_count': overall_quantum,
            'quantum_percentage': round(overall_quantum / overall_total * 100, 4) if overall_total else 0.0,
        },
    }
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'RQ4 saved to {output_file}: {overall_quantum}/{overall_total} '
          f'({results["overall"]["quantum_percentage"]}%) quantum-specific SCCUs')

if __name__ == '__main__':
    main()
