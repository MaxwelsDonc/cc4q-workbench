import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, FuncFormatter
from matplotlib.transforms import blended_transform_factory
entities = ['Function', 'Class', 'Module']
forms = ['Docstring', 'Block', 'Inline']
quantum = np.array([[4255, 1322, 54], [1181, 25, 3], [641, 296, 1]], dtype=float)
total = np.array([[11888, 3889, 393], [2461, 192, 18], [1785, 1306, 38]], dtype=float)
non_quantum = total - quantum
COLOR_Q = '#1f77b4'
COLOR_NQ = '#bdbdbd'

def create_bar_chart():
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    overall_q = float(np.sum(quantum))
    overall_t = float(np.sum(total))
    ent_order = [2, 1, 0]
    ent_q = np.sum(quantum, axis=1)[ent_order]
    ent_t = np.sum(total, axis=1)[ent_order]
    ent_lbs = [entities[i] for i in ent_order]
    form_order = [0, 1, 2]
    form_q = np.sum(quantum, axis=0)[form_order]
    form_t = np.sum(total, axis=0)[form_order]
    form_lbs = [forms[i] for i in form_order]
    small_gap = 0.5
    big_gap = 1.0
    x_overall = np.array([0.0])
    g2_start = x_overall[-1] + big_gap
    x_entities = g2_start + np.array([0.0, small_gap, small_gap * 2.0])
    g3_start = x_entities[-1] + big_gap
    x_forms = g3_start + np.array([0.0, small_gap, small_gap * 2.0])
    xs = np.concatenate([x_overall, x_entities, x_forms])
    labels = ['Total'] + ent_lbs + form_lbs
    q_vals = [overall_q] + list(ent_q) + list(form_q)
    t_vals = [overall_t] + list(ent_t) + list(form_t)
    pct_q = [q / t if t > 0 else 0.0 for q, t in zip(q_vals, t_vals)]
    bar_width = 0.38
    ax.bar(xs, pct_q, width=bar_width, color=COLOR_Q, edgecolor='white', linewidth=0.8)
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f'{int(round(v * 100))}%'))
    ax.set_ylabel('Proportion of quantum SCCUs')
    ax.set_xticks(xs, labels)
    ax.tick_params(axis='x', which='both', pad=8)
    ax.set_xlabel('')
    mid_g1_g2 = (x_overall[-1] + x_entities[0]) / 2.0
    mid_g2_g3 = (x_entities[-1] + x_forms[0]) / 2.0
    ax.axvline(x=mid_g1_g2, color='#666666', linestyle='--', linewidth=1.0)
    ax.axvline(x=mid_g2_g3, color='#666666', linestyle='--', linewidth=1.0)
    for x0, qv, tv, p in zip(xs, q_vals, t_vals, pct_q):
        if tv > 0:
            ax.text(x0, min(p + 0.02, 1.02), f'{p * 100:.1f}%', ha='center', va='bottom', fontsize=11, bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1.5), linespacing=1.2)
    trans = blended_transform_factory(ax.transData, ax.transAxes)
    g2_center = (x_entities[0] + x_entities[-1]) / 2.0
    g3_center = (x_forms[0] + x_forms[-1]) / 2.0
    ax.text(g2_center, -0.1, 'Code entities', transform=trans, ha='center', va='top', fontsize=11)
    ax.text(g3_center, -0.1, 'Comment forms', transform=trans, ha='center', va='top', fontsize=11)
    ax.grid(axis='y', color='#e6e6e6', linestyle='-', linewidth=0.8)
    fig.subplots_adjust(bottom=0.2, left=0.08, right=0.98, top=0.9)
    return fig
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

def create_donut_chart():
    fig, ax = plt.subplots(figsize=(6, 5.4))
    ax.set_xlim(-0.5, len(entities) - 0.5)
    ax.set_ylim(-0.5, len(forms) - 0.5)
    ax.set_xticks(np.arange(len(entities)), entities)
    ax.set_yticks(np.arange(len(forms)), forms)
    ax.tick_params(axis='x', which='both', pad=12)
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_axisbelow(True)
    ax.grid(color='#e6e6e6', linestyle='-', linewidth=0.8)
    fig.subplots_adjust(bottom=0.2, left=0.02, right=0.98, top=0.92)
    fig.canvas.draw()
    const_side_px = 150
    size_in = const_side_px / fig.dpi
    for i, form in enumerate(forms):
        for j, ent in enumerate(entities):
            q = float(quantum[j, i])
            nq = float(non_quantum[j, i])
            s = q + nq
            if s <= 0:
                continue
            ax_frac = ax.transAxes.inverted().transform(ax.transData.transform((j, i)))
            ax_x, ax_y = ax_frac
            pie_ax = inset_axes(ax, width=size_in, height=size_in, loc='center', bbox_to_anchor=(ax_x, ax_y, 0, 0), bbox_transform=ax.transAxes, borderpad=0)
            pct_q = 100.0 * q / s
            pie_ax.pie([q, nq], startangle=90, counterclock=False, colors=[COLOR_Q, COLOR_NQ], wedgeprops={'linewidth': 0.6, 'edgecolor': 'white', 'width': 0.35}, labels=None)
            pie_ax.text(0, 0.3, f'{pct_q:.1f}%', ha='center', va='center', fontsize=12, color='#333333')
            pie_ax.text(0, -0.3, f'$\\frac{{{int(q):,}}}{{{int(s):,}}}$', ha='center', va='center', fontsize=12, color='#333333')
            pie_ax.set_aspect('equal')
            pie_ax.axis('off')
    return fig

def create_legend_chart():
    fig, ax = plt.subplots(figsize=(2.8, 0.6))
    ax.axis('off')
    ax.scatter(0.1, 0.5, s=120, c=COLOR_Q, edgecolors='black', linewidth=0.5)
    ax.text(0.2, 0.5, 'quantum', va='center', ha='left', fontsize=12)
    ax.scatter(0.55, 0.5, s=120, c=COLOR_NQ, edgecolors='black', linewidth=0.5)
    ax.text(0.65, 0.5, 'non-quantum', va='center', ha='left', fontsize=12)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.subplots_adjust(bottom=0, left=0, right=1, top=1)
    return fig

def main():
    output_dir = 'rqs/distribution_based/visualization/img'
    os.makedirs(output_dir, exist_ok=True)
    print(f'输出目录已创建或已存在: {output_dir}')
    print('正在生成分组堆叠柱状图...')
    bar_fig = create_bar_chart()
    bar_output_path = os.path.join(output_dir, 'rq3_bar_chart.pdf')
    bar_fig.savefig(bar_output_path, format='pdf', bbox_inches='tight', dpi=300)
    plt.close(bar_fig)
    print(f'分组堆叠柱状图已保存: {bar_output_path}')
    print('正在生成图例图片...')
    legend_fig = create_legend_chart()
    legend_output_path = os.path.join(output_dir, 'rq3_legend.pdf')
    legend_fig.savefig(legend_output_path, format='pdf', bbox_inches='tight', dpi=300)
    plt.close(legend_fig)
    print(f'图例图片已保存: {legend_output_path}')
    print('正在生成甜甜圈图矩阵...')
    donut_fig = create_donut_chart()
    donut_output_path = os.path.join(output_dir, 'rq3_donut_chart.pdf')
    donut_fig.savefig(donut_output_path, format='pdf', bbox_inches='tight', dpi=300)
    plt.close(donut_fig)
    print(f'甜甜圈图矩阵已保存: {donut_output_path}')
    print('\n=== 图表生成完成 ===')
    print(f'1. 分组堆叠柱状图: {bar_output_path}')
    print(f'2. 甜甜圈图矩阵: {donut_output_path}')
    print(f'3. 图例图片: {legend_output_path}')
    print('\n三个PDF文件已成功生成！')
if __name__ == '__main__':
    main()
