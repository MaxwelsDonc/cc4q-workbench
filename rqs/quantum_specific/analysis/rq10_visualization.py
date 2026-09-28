import json
import os
from setup_path import parent_root, figure_global
import matplotlib.pyplot as plt
import plotly.graph_objs as go
import numpy as np
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
embeddings_file = os.path.join(project_root, 'results', 'rq10_2d_embeddings.json')
similarity_file = os.path.join(project_root, 'results', 'rq10_similarity_matrix.json')
output_2d_pdf = os.path.join(project_root, 'visualization', 'rq10_2d_embeddings.pdf')
output_bubble_pdf = os.path.join(project_root, 'visualization', 'rq10_similarity_bubble.pdf')

def embedding_plot(embedding_data):
    res_dict = {}
    _, ax = plt.subplots(figsize=(5, 4))
    plt.grid(True, color='#d3d3d3', linestyle='--', linewidth=0.8)
    plt.axhline(0, color='black', linestyle=':', linewidth=0.8)
    plt.axvline(0, color='black', linestyle=':', linewidth=0.8)
    colors = plt.cm.tab10(np.linspace(0, 1, len(embedding_data)))
    all_x, all_y = ([], [])
    for i, (category, data_list) in enumerate(embedding_data.items()):
        embedding_list = [point_dict['embedding_3d'][:2] for point_dict in data_list]
        embedding_array = np.array(embedding_list)
        center = embedding_array.mean(axis=0)
        distances = np.linalg.norm(embedding_array - center, axis=1)
        radius = distances.max()
        res_dict[category] = {'center': center.tolist(), 'radius': radius}
        all_x.append(center[0])
        all_y.append(center[1])
        plt.scatter(center[0], center[1], marker='D', color=colors[i], s=60, label=category)
        plt.text(center[0], center[1] + 1.5, category, fontsize=8, ha='center', va='bottom')
    plt.xlabel('X for 2-dimensional embeddings', fontsize=12, labelpad=8)
    plt.ylabel('Y for 2-dimensional embeddings', fontsize=12, labelpad=8)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    if all_x and all_y:
        x_min, x_max = (min(all_x), max(all_x))
        y_min, y_max = (min(all_y), max(all_y))
        x_margin = (x_max - x_min) * 0.28 if x_max > x_min else 1
        y_margin = (y_max - y_min) * 0.1 if y_max > y_min else 1
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
    plt.tight_layout()
    plt.savefig(output_2d_pdf, format='pdf', dpi=600, bbox_inches='tight')
    plt.close()

def bubble_plot(similarity_data, show_values=True, axis_fontsize=10, data_fontsize=8, legend_fontsize=8):
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np
    category_order = similarity_data['category_order']
    sim_matrix = similarity_data['sim_matrix']
    n = len(category_order)
    y_order = category_order[::-1]
    df_sim = pd.DataFrame(sim_matrix, index=similarity_data['category_order'], columns=similarity_data['category_order'])
    df_sim = df_sim.loc[category_order, category_order]
    fig, ax = plt.subplots(figsize=(5, 4))
    for i in range(n):
        for j in range(n):
            if i + j < n - 1:
                rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor='#f3f2f2', edgecolor='none', zorder=0)
                ax.add_patch(rect)
    values_to_plot, coords = ([], [])
    for i, y_cat in enumerate(y_order):
        for j, x_cat in enumerate(category_order):
            if i + j < n - 1:
                value = df_sim.loc[y_cat, x_cat]
                values_to_plot.append(value)
                coords.append((i, j))
    values_to_plot = np.array(values_to_plot)
    max_radius = 800
    min_radius = 50
    min_val, max_val = (values_to_plot.min(), values_to_plot.max())
    bubble_sizes = min_radius + (max_radius - min_radius) * (values_to_plot - min_val) / (max_val - min_val + 1e-08)
    for (i, j), value, size in zip(coords, values_to_plot, bubble_sizes):
        y_idx = i
        ax.scatter(j, y_idx, s=size, color='#f9c5ce', edgecolors='none', zorder=2)
        if show_values:
            ax.text(j, y_idx, f'{value:.2f}', ha='center', va='center', fontsize=data_fontsize, zorder=3)
    ax.set_xticks(np.arange(n - 1))
    ax.set_yticks(np.arange(n - 1))
    ax.set_xticklabels(category_order[:n - 1], rotation=25, ha='right', fontsize=axis_fontsize)
    ax.set_yticklabels(y_order[:n - 1], fontsize=axis_fontsize)
    max_j = max((j for _, j in coords))
    ax.set_xlim(-0.5, max_j + 0.5)
    max_i = max((i for i, _ in coords))
    ax.set_ylim(-0.5, max_i + 0.5)
    ax.grid(True, color='white', linestyle='-', linewidth=1.0, zorder=1)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    legend_quantiles = [0.25, 0.5, 0.75, 1.0]
    quantile_vals = np.quantile(values_to_plot, legend_quantiles)
    handles = [plt.scatter([], [], s=min_radius + (max_radius - min_radius) * (val - min_val) / (max_val - min_val + 1e-08), color='#f9c5ce', edgecolors='none') for val in quantile_vals]
    labels = [f'{val:.2f}' for val in quantile_vals]
    ax.legend(handles, labels, scatterpoints=1, frameon=True, edgecolor='black', fontsize=legend_fontsize, title_fontsize=legend_fontsize, loc='upper left', bbox_to_anchor=(0.66, 1), labelspacing=2.5, borderaxespad=0, handletextpad=1.1, markerscale=1, borderpad=1.5)
    plt.tight_layout()
    plt.savefig(output_bubble_pdf, format='pdf', dpi=600, bbox_inches='tight')
    plt.close()

def rq10_figures():
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)
    with open(similarity_file, 'r', encoding='utf-8') as f:
        similarity_data = json.load(f)
    embedding_plot(embeddings_data)
    bubble_plot(similarity_data)
if __name__ == '__main__':
    rq10_figures()
