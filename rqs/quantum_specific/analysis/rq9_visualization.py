import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cooccurrence_file = os.path.join(project_root, 'results', 'rq9_cooccurrence_jaccard.json')
correlation_file = os.path.join(project_root, 'results', 'rq9_correlation_pearson.json')
output_pdf_cooccurrence = os.path.join(project_root, 'visualization', 'rq9_cooccurrence_heatmap.pdf')
output_pdf_correlation = os.path.join(project_root, 'visualization', 'rq9_correlation_heatmap.pdf')

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
data_cooccurrence = load_json(cooccurrence_file)
data_correlation = load_json(correlation_file)

def dict_to_dataframe(data_dict):
    return pd.DataFrame.from_dict(data_dict, orient='index')
df_cooccurrence = dict_to_dataframe(data_cooccurrence)
df_correlation = dict_to_dataframe(data_correlation)
plt.rcParams.update({'font.size': 10, 'axes.labelsize': 10, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
figsize = (5, 4)
labelsize = 10
plt.figure(figsize=figsize)
ax = sns.heatmap(df_cooccurrence, annot=True, cmap='YlGnBu', cbar=True, fmt='.2f')
plt.xticks(rotation=25, ha='right')
plt.yticks(rotation=0)
ax.collections[0].colorbar.ax.tick_params(labelsize=labelsize)
plt.tight_layout()
plt.savefig(output_pdf_cooccurrence, format='pdf', dpi=600)
plt.close()
print(f'Co-occurrence heatmap generated:\n{output_pdf_cooccurrence}')
plt.figure(figsize=figsize)
ax = sns.heatmap(df_correlation, annot=True, cmap=sns.diverging_palette(220, 20, as_cmap=True), center=0, cbar=True, fmt='.2f')
plt.xticks(rotation=25, ha='right')
plt.yticks(rotation=0)
ax.collections[0].colorbar.ax.tick_params(labelsize=labelsize)
plt.tight_layout()
plt.savefig(output_pdf_correlation, format='pdf', dpi=600)
plt.close()
print(f'Correlation heatmap generated:\n{output_pdf_correlation}')
