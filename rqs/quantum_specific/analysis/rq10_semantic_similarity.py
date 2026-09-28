from sentence_transformers import SentenceTransformer
import numpy as np
import warnings
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.manifold import TSNE
import json
import os
import argparse
file_root = os.path.dirname(__file__)
parent_file_root = os.path.dirname(file_root)
warnings.filterwarnings('ignore', category=FutureWarning)
save_sim_matrix = 'rq10_similarity_matrix.json'
save_vis_embeddings = 'rq10_2d_embeddings.json'

def semantic_similarity(data, perplexity=30):
    num_ccps = len(data)
    model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
    embeddings_raw = defaultdict(list)
    all_embeddings = []
    trace_data = []
    for data_unit_dict in data:
        quan_category = data_unit_dict['quantum_specific_category']
        comment = data_unit_dict['comment_text']
        comment_id = data_unit_dict['id']
        if quan_category:
            embedding = model.encode(comment)
            embeddings_raw[quan_category].append(embedding)
            all_embeddings.append(embedding)
            trace_data.append({'id': comment_id, 'category': quan_category})
    category_embeddings = {}
    for quan_category, embedding_list in embeddings_raw.items():
        centroid = np.mean(embedding_list, axis=0)
        category_embeddings[quan_category] = centroid
    category_order = list(category_embeddings.keys())
    centroids = [centroid for centroid in category_embeddings.values()]
    centroids = np.array(centroids)
    sim_matrix = cosine_similarity(centroids)
    sim_output_dict = {'category_order': category_order, 'sim_matrix': sim_matrix.tolist()}
    all_embeddings_2d = TSNE(n_components=2, perplexity=num_ccps - 1 if num_ccps < perplexity else perplexity, random_state=42).fit_transform(np.array(all_embeddings))
    embeddings_2d = {}
    for list_id, embedding_2d in enumerate(all_embeddings_2d):
        comment_category = trace_data[list_id]['category']
        comment_id = trace_data[list_id]['id']
        if embeddings_2d.get(comment_category) is None:
            embeddings_2d[comment_category] = []
        embeddings_2d[comment_category].append({'id': comment_id, 'embedding_2d': embedding_2d.tolist()})
    with open(os.path.join(parent_file_root, 'results', save_sim_matrix), 'w', encoding='utf-8') as f:
        json.dump(sim_output_dict, f, indent=2, ensure_ascii=False)
    with open(os.path.join(parent_file_root, 'results', save_vis_embeddings), 'w', encoding='utf-8') as f:
        json.dump(embeddings_2d, f, indent=2, ensure_ascii=False)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Return the empirical results based on the datasset')
    parser.add_argument('file', type=str, help='Input the file of the json dataset')
    args = parser.parse_args()
    file_dir = args.file
    with open(file_dir, 'r', encoding='utf-8') as f:
        total_data = [json.loads(line) for line in f]
    semantic_similarity(total_data)
