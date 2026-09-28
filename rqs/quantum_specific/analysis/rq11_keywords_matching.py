import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.feature_selection import mutual_info_classif
from collections import defaultdict
import numpy as np
import re
import json
import os
import argparse
nltk.download('punkt_tab', quiet=True)
file_root = os.path.dirname(__file__)
save_dir = os.path.join(os.path.dirname(file_root), 'results')
os.makedirs(save_dir, exist_ok=True)
cover_file = os.path.join(save_dir, 'rq11_class_coverage.json')
tfidf_file = os.path.join(save_dir, 'rq11_class_tfidf.json')
mi_file = os.path.join(save_dir, 'rq11_mutual_info.json')

def keyword_coverage(keyword_vocab, category_tokens, stem_map, max_n):
    keyword_set = set(keyword_vocab)
    coverage_stats = {}
    for cate, comments_tokens in category_tokens.items():
        total_count = 0
        covered_keywords = set()
        for tokens in comments_tokens:
            found_ngrams = set()
            for n in range(1, max_n + 1):
                for i in range(len(tokens) - n + 1):
                    ng = ' '.join(tokens[i:i + n])
                    if ng in keyword_set:
                        found_ngrams.add(ng)
            total_count += len(found_ngrams)
            covered_keywords.update(found_ngrams)
        coverage_stats[cate] = {'total_covered_count': total_count, 'unique_covered_keywords': [stem_map[w] for w in covered_keywords], 'coverage_ratio': len(covered_keywords) / len(keyword_vocab)}
    return coverage_stats

def tfidf_analysis(comment_texts, comment_cates, keyword_vocab, stem_map, max_n):
    vectorizer = TfidfVectorizer(vocabulary=keyword_vocab, ngram_range=(1, max_n))
    tfidf_matrix = vectorizer.fit_transform(comment_texts)
    feature_names = vectorizer.get_feature_names_out()
    res_tfidf = {}
    tag_comments = defaultdict(list)
    for cate, text in zip(comment_cates, comment_texts):
        tag_comments[cate].append(text)
    for comment_cate, comments in tag_comments.items():
        indices = [comment_texts.index(c) for c in comments]
        cat_scores = np.asarray(tfidf_matrix[indices].sum(axis=0)).flatten()
        tfidf_indices = cat_scores.argsort()[::-1]
        res_tfidf[comment_cate] = {}
        order_tfidf, last_val_tfidf = (1, None)
        for i in tfidf_indices:
            if cat_scores[i] <= 0:
                continue
            word = stem_map[str(feature_names[i])]
            val = cat_scores[i]
            if last_val_tfidf is None:
                last_val_tfidf = val
            elif val < last_val_tfidf:
                order_tfidf += 1
                last_val_tfidf = val
            res_tfidf[comment_cate][word] = {'tf-idf': val, 'top': order_tfidf}
    return res_tfidf

def mifs_analysis(comment_texts, comment_cates, keyword_vocab, stem_map, max_n, beta=0.6):
    count_vectorizer = CountVectorizer(vocabulary=keyword_vocab, ngram_range=(1, max_n))
    X_counts = count_vectorizer.fit_transform(comment_texts)
    feature_names_counts = count_vectorizer.get_feature_names_out()
    all_labels = np.array(comment_cates)
    mi_scores = {}
    for tag in set(comment_cates):
        y_binary = np.array([1 if lbl == tag else 0 for lbl in all_labels])
        mask = X_counts.sum(axis=0).A1 > 0
        X_sub = X_counts[:, mask].toarray()
        features_sub = feature_names_counts[mask]
        n_features = X_sub.shape[1]
        mi_vals = mutual_info_classif(X_sub, y_binary, discrete_features=True)
        selected_idx, remaining_idx = ([], list(range(n_features)))
        mifs_scores, top_ranks = (np.zeros(n_features), np.zeros(n_features, dtype=int))
        rank_counter = 1
        while remaining_idx:
            score_candidates = []
            for idx in remaining_idx:
                redundancy = 0
                for sel in selected_idx:
                    xi, xj = (X_sub[:, idx], X_sub[:, sel])
                    redundancy += mutual_info_classif(xi.reshape(-1, 1), xj, discrete_features=True)[0]
                mifs_score = mi_vals[idx] - beta * redundancy
                score_candidates.append((mifs_score, idx))
            score_candidates.sort(reverse=True)
            best_score, best_idx = score_candidates[0]
            if best_score <= 0:
                break
            selected_idx.append(best_idx)
            remaining_idx.remove(best_idx)
            mifs_scores[best_idx] = best_score
            top_ranks[best_idx] = rank_counter
            rank_counter += 1
        tag_scores = {}
        for i, feat in enumerate(features_sub):
            score = float(mifs_scores[i])
            if score > 0:
                word = stem_map[str(feat)]
                tag_scores[word] = {'mifs_score': score, 'top': int(top_ranks[i])}
        mi_scores[tag] = dict(sorted(tag_scores.items(), key=lambda x: x[1]['mifs_score'], reverse=True))
    return mi_scores

def keyword_matching(data, keywords, use_stemming=True):
    stemmer = PorterStemmer()

    def preprocess(text):
        tokens = word_tokenize(text.lower())
        tokens = [t for t in tokens if t.isalpha()]
        if use_stemming:
            tokens = [stemmer.stem(t) for t in tokens]
        return tokens
    keywords = [re.sub('[-_]', ' ', keyword) for keyword in keywords]
    if use_stemming:
        stem_map = {stemmer.stem(w.lower()): w for w in keywords}
        keyword_vocab = list(stem_map.keys())
    else:
        stem_map = {w.lower(): w for w in keywords}
        keyword_vocab = list(stem_map.keys())
    comment_texts = []
    comment_cates = []
    category_tokens = defaultdict(list)
    for data_unit_dict in data:
        comment = data_unit_dict['comment_text']
        quan_category = data_unit_dict['quantum_specific_category']
        if quan_category:
            tokens = preprocess(comment)
            comment_texts.append(tokens)
            comment_cates.append(quan_category)
            category_tokens[quan_category].append(tokens)
    max_n = max(1, max((len(k.split()) for k in keyword_vocab)))
    res_coverage = keyword_coverage(keyword_vocab, category_tokens, stem_map, max_n)
    res_tf_idf = tfidf_analysis([' '.join(t) for t in comment_texts], comment_cates, keyword_vocab, stem_map, max_n)
    res_mi_scores = mifs_analysis([' '.join(t) for t in comment_texts], comment_cates, keyword_vocab, stem_map, max_n)
    with open(cover_file, 'w', encoding='utf-8') as f:
        json.dump(res_coverage, f, indent=2, ensure_ascii=False)
    with open(tfidf_file, 'w', encoding='utf-8') as f:
        json.dump(res_tf_idf, f, indent=2, ensure_ascii=False)
    with open(mi_file, 'w', encoding='utf-8') as f:
        json.dump(res_mi_scores, f, indent=2, ensure_ascii=False)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Return category-specific keywords')
    parser.add_argument('file', type=str, help='Input JSONL dataset file')
    args = parser.parse_args()
    file_dir = args.file
    with open(file_dir, 'r', encoding='utf-8') as f:
        total_data = [json.loads(line) for line in f]
    file_name = 'keyword_list.json'
    target_file_root = os.path.dirname(os.path.dirname(file_root))
    with open(os.path.join(target_file_root, file_name), 'r', encoding='utf-8') as f:
        keywords = json.load(f)
    keyword_matching(total_data, keywords)
