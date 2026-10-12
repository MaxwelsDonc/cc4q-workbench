from setup_path import parent_root, cat2tex
import os
import json

def centering_header(header, last_one=False):
    if last_one:
        return f'\\multicolumn{{1}}{{c}}{{\\textbf{{{header}}}}}'
    else:
        return f'\\multicolumn{{1}}{{c|}}{{\\textbf{{{header}}}}}'

def rq11_latex_code(top_k=5):
    res_dict = {'coverage': 'rq11_class_coverage.json', 'tf_idf': 'rq11_class_tfidf.json', 'mifs': 'rq11_mutual_info.json'}
    data_dict = {}
    for res_file in res_dict.values():
        temp_dir = os.path.join(parent_root, 'results', res_file)
        with open(temp_dir, 'r', encoding='utf-8') as f:
            temp_data = json.load(f)
        data_dict[res_file] = temp_data
    data_content = ''
    for cat_name, cat_tex in cat2tex.items():
        if 'quantum' in cat_name:
            data_content += ' \\midrule\n    '
            data_content += f'{cat_tex} & '
            cov_dict = data_dict[res_dict['coverage']]
            cov_val = cov_dict[cat_name]['coverage_ratio']
            cov_str = '{:.2g}'.format(cov_val)
            data_content += f'{cov_str} & '
            tfidf_dict = data_dict[res_dict['tf_idf']]
            for idx, (keyword_str, keyword_val) in enumerate(tfidf_dict[cat_name].items()):
                if idx < top_k:
                    val_str = str(round(keyword_val['tf-idf']))
                    if idx == 0:
                        data_content += f"``{keyword_str}'' ({val_str})"
                    else:
                        data_content += f", ``{keyword_str}'' ({val_str})"
                else:
                    break
            data_content += ' & '
            mifs_dict = data_dict[res_dict['mifs']]
            for idx, (keyword_str, keyword_val) in enumerate(mifs_dict[cat_name].items()):
                if idx < top_k:
                    val_str = '{:.1e}'.format(keyword_val['mifs_score'])
                    if idx == 0:
                        data_content += f"``{keyword_str}'' ({val_str})"
                    else:
                        data_content += f", ``{keyword_str}'' ({val_str})"
                else:
                    break
            data_content += ' \\\\\n    '
    latex_code = f"\n\\begin{{tabular}}{{p{{0.14\\textwidth}}|c|p{{0.42\\textwidth}}|p{{0.42\\textwidth}}}}\n    \\toprule[1.25pt]\n\n    {centering_header('Categories')} & {centering_header('Coverage')} & {centering_header('c-TF-IDF')} \n    & {centering_header('MIFS', last_one=True)} \\\\\n    {data_content}\n    \\bottomrule[1.25pt]\n\\end{{tabular}}\n    "
    return latex_code
if __name__ == '__main__':
    latex_code = rq11_latex_code()
    save_dir = os.path.join(parent_root, 'visualization')
    os.makedirs(save_dir, exist_ok=True)
    save_file = os.path.join(save_dir, f'RQ11_table.tex')
    with open(save_file, 'w', encoding='utf-8') as f:
        f.write(latex_code)
