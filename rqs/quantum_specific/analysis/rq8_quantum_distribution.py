import numpy as np
from sklearn.metrics import jaccard_score
from scipy.stats import pearsonr
import os
import json
import argparse
file_root = os.path.dirname(__file__)
parent_file_root = os.path.dirname(file_root)
save_dist = 'rq8_distribution.json'

def quantum_distribution(data):
    dis_dict = {}
    num_quan_ccps = 0
    for data_unit_dict in data:
        quan_cat = data_unit_dict['quantum_specific_category']
        if quan_cat is not None:
            num_quan_ccps += 1
            if quan_cat not in dis_dict:
                dis_dict[quan_cat] = {}
                dis_dict[quan_cat]['freqs'] = 1
            else:
                dis_dict[quan_cat]['freqs'] += 1
    for quan_cat in dis_dict.keys():
        dis_dict[quan_cat]['prop'] = dis_dict[quan_cat]['freqs'] / num_quan_ccps
    with open(os.path.join(parent_file_root, 'results', save_dist), 'w', encoding='utf-8') as f:
        json.dump(dis_dict, f, indent=2, ensure_ascii=False)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Return the empirical results based on the datasset')
    parser.add_argument('file', type=str, help='Input the file of the jsonl dataset')
    args = parser.parse_args()
    file_dir = args.file
    with open(file_dir, 'r', encoding='utf-8') as f:
        total_data = [json.loads(line) for line in f]
    quantum_distribution(total_data)
