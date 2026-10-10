import json
import random
from collections import Counter
from pathlib import Path
input_file = Path('model/quantum_category_classifier/data/all_data_r12.jsonl')
output_file = Path('model/quantum_category_classifier/data/all_data_r12_balanced.jsonl')
target_count = 300
random.seed(42)
data = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))
label_counts = Counter((d['label'] for d in data))
print('Original class distribution:', label_counts)
balanced_data = []
for label in sorted(label_counts.keys()):
    samples = [d for d in data if d['label'] == label]
    count = len(samples)
    if count < target_count:
        extra = random.choices(samples, k=target_count - count)
        new_samples = samples + extra
    elif count > target_count:
        new_samples = random.sample(samples, target_count)
    else:
        new_samples = samples
    balanced_data.extend(new_samples)
random.shuffle(balanced_data)
with open(output_file, 'w', encoding='utf-8') as f:
    for item in balanced_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
new_counts = Counter((d['label'] for d in balanced_data))
print('Balanced class distribution:', new_counts)
print(f'Saved to: {output_file}')
