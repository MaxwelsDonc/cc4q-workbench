import numpy as np
from sklearn.metrics import jaccard_score
from scipy.stats import pearsonr
import os
import json
import argparse
file_root = os.path.dirname(__file__)
parent_file_root = os.path.dirname(file_root)
save_pearson = 'rq9_correlation_pearson.json'
save_jaccard = 'rq9_cooccurrence_jaccard.json'

def binary_vectors(data):
    dev_categories, quan_categories = ([], [])
    quan_data = []
    for data_unit_dict in data:
        dev_cat = data_unit_dict['developer_intent_category']
        quan_cat = data_unit_dict['quantum_specific_category']
        if dev_cat is not None:
            dev_categories.append(dev_cat)
        if quan_cat is not None:
            quan_categories.append(quan_cat)
            quan_data.append(data_unit_dict)
    dev_categories, quan_categories = (list(set(dev_categories)), list(set(quan_categories)))
    boolean_vec_dict = {'developer': {}, 'quantum': {}, 'ids': []}
    for data_unit_dict in quan_data:
        boolean_vec_dict['ids'].append(data_unit_dict['id'])
        dev_cat = data_unit_dict['developer_intent_category']
        quan_cat = data_unit_dict['quantum_specific_category']
        for enum_dev_tag in dev_categories:
            if boolean_vec_dict['developer'].get(enum_dev_tag) is None:
                boolean_vec_dict['developer'][enum_dev_tag] = [bool(dev_cat == enum_dev_tag)]
            else:
                boolean_vec_dict['developer'][enum_dev_tag].append(bool(dev_cat == enum_dev_tag))
        for enum_quan_cat in quan_categories:
            if boolean_vec_dict['quantum'].get(enum_quan_cat) is None:
                boolean_vec_dict['quantum'][enum_quan_cat] = [bool(quan_cat == enum_quan_cat)]
            else:
                boolean_vec_dict['quantum'][enum_quan_cat].append(bool(quan_cat == enum_quan_cat))
    return boolean_vec_dict

def compute_jaccard_and_pearson(boolean_vec_dict):
    dev_categories = list(boolean_vec_dict['developer'].keys())
    quan_categories = list(boolean_vec_dict['quantum'].keys())
    jaccard_matrix = {}
    pearson_matrix = {}
    for dev_tag in dev_categories:
        jaccard_matrix[dev_tag] = {}
        pearson_matrix[dev_tag] = {}
        dev_vec = boolean_vec_dict['developer'][dev_tag]
        for quan_cat in quan_categories:
            quan_vec = boolean_vec_dict['quantum'][quan_cat]
            dev_arr = np.array(dev_vec, dtype=int)
            quan_arr = np.array(quan_vec, dtype=int)
            jaccard = jaccard_score(dev_arr, quan_arr)
            jaccard_matrix[dev_tag][quan_cat] = jaccard
            if np.std(dev_arr) == 0 or np.std(quan_arr) == 0:
                pearson = 0.0
            else:
                pearson, _ = pearsonr(dev_arr, quan_arr)
            pearson_matrix[dev_tag][quan_cat] = pearson
    with open(os.path.join(parent_file_root, 'results', save_jaccard), 'w', encoding='utf-8') as f:
        json.dump(jaccard_matrix, f, indent=2, ensure_ascii=False)
    with open(os.path.join(parent_file_root, 'results', save_pearson), 'w', encoding='utf-8') as f:
        json.dump(pearson_matrix, f, indent=2, ensure_ascii=False)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Return the empirical results based on the datasset')
    parser.add_argument('file', type=str, help='Input the file of the jsonl dataset')
    args = parser.parse_args()
    file_dir = args.file
    with open(file_dir, 'r', encoding='utf-8') as f:
        total_data = [json.loads(line) for line in f]
    bool_vec_dict = binary_vectors(total_data)
    compute_jaccard_and_pearson(bool_vec_dict)
