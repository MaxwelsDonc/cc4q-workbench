import json
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_file = os.path.join(project_root, 'results', 'rq8_distribution.json')
output_pdf = os.path.join(project_root, 'visualization', 'rq8_bar_chart.pdf')
with open(data_file, 'r', encoding='utf-8') as f:
    rq8_data = json.load(f)
categories = list(rq8_data.keys())
freqs = [rq8_data[cat]['freqs'] for cat in categories]
props = [rq8_data[cat]['prop'] for cat in categories]
fig, ax = plt.subplots(figsize=(8, 2))
y = np.arange(len(categories))
bar_height = 0.25
bars = ax.barh(y, freqs, height=bar_height, color='#4C72B0', alpha=0.85, edgecolor='black')
ax.set_ylim(-0.5, len(categories) - 0.5)
ax.set_xlim(0, max(freqs) * 1.18)
for i, bar in enumerate(bars):
    value = freqs[i]
    percent = props[i] * 100
    ax.text(bar.get_width() + max(freqs) * 0.01, bar.get_y() + bar.get_height() / 2, f'{value} ({percent:.1f}%)', va='center', ha='left', fontsize=10)
ax.set_yticks(y)
ax.set_yticklabels(categories, fontsize=10)
ax.set_ylabel('Categories', fontsize=12)
ax.set_xlabel('# of SCCUs', fontsize=12)
ax.tick_params(axis='x', labelsize=10)
ax.grid(axis='x', linestyle='--', alpha=0.6)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
plt.savefig(output_pdf, format='pdf', dpi=300, bbox_inches='tight')
plt.close()
print(f'Bar chart saved: {output_pdf}')
