#!/usr/bin/env python3

import json
import os

def load_rq4_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['quantum_proportion_distribution']

def aggregate_by_entity(data):
    entities = {'function': {}, 'class': {}, 'module': {}}
    for key, value in data.items():
        entity_type = value['code_entity']
        comment_form = value['comment_forms']
        total_count = value['total_count']
        quantum_count = value['quantum_count']
        quantum_percentage = value['quantum_percentage']
        if entity_type in entities:
            entities[entity_type][comment_form] = {'total_count': total_count, 'quantum_count': quantum_count, 'quantum_percentage': quantum_percentage}
    return entities

def calculate_totals(entities):
    totals = {}
    quantum_totals = {}
    overall_total = 0
    overall_quantum = 0
    for entity_type, comments in entities.items():
        entity_total = sum((data['total_count'] for data in comments.values()))
        entity_quantum = sum((data['quantum_count'] for data in comments.values()))
        totals[entity_type] = entity_total
        quantum_totals[entity_type] = entity_quantum
        overall_total += entity_total
        overall_quantum += entity_quantum
    return (totals, quantum_totals, overall_total, overall_quantum)

def generate_latex_table(entities, output_file):
    totals, quantum_totals, overall_total, overall_quantum = calculate_totals(entities)
    entity_names = {'function': 'Functions', 'class': 'Classes', 'module': 'Modules'}
    comment_forms = ['docstring', 'block', 'inline']
    latex_content = []
    latex_content.append('\\begin{tabular}{lccccc}')
    latex_content.append('\\hline')
    latex_content.append('\\textbf{Entity Type} & \\textbf{Docstring} & \\textbf{Block} & \\textbf{Inline} & \\textbf{Total} \\\\')
    latex_content.append('\\hline')
    for entity_type in ['function', 'class', 'module']:
        entity_data = entities[entity_type]
        entity_name = entity_names[entity_type]
        entity_total = totals[entity_type]
        entity_quantum = quantum_totals[entity_type]
        count_row_parts = [f'\\textbf{{{entity_name}}}']
        for comment_form in comment_forms:
            if comment_form in entity_data:
                quantum_count = entity_data[comment_form]['quantum_count']
                total_count = entity_data[comment_form]['total_count']
                count_row_parts.append(f'{quantum_count} / {total_count}')
            else:
                count_row_parts.append('0 / 0')
        count_row_parts.append(f'{entity_quantum} / {entity_total}')
        latex_content.append(' & '.join(count_row_parts) + ' \\\\')
        percentage_row_parts = ['']
        for comment_form in comment_forms:
            if comment_form in entity_data:
                percentage = entity_data[comment_form]['quantum_percentage']
                percentage_row_parts.append(f'({percentage:.2f}\\%)')
            else:
                percentage_row_parts.append('(0.00\\%)')
        entity_percentage = round(entity_quantum / entity_total * 100, 2) if entity_total > 0 else 0.0
        percentage_row_parts.append(f'({entity_percentage:.2f}\\%)')
        latex_content.append(' & '.join(percentage_row_parts) + ' \\\\')
        latex_content.append('\\hline')
    total_count_row_parts = ['\\textbf{Total}']
    for comment_form in comment_forms:
        form_total = 0
        form_quantum = 0
        for entity_type in ['function', 'class', 'module']:
            if comment_form in entities[entity_type]:
                form_total += entities[entity_type][comment_form]['total_count']
                form_quantum += entities[entity_type][comment_form]['quantum_count']
        total_count_row_parts.append(f'{form_quantum} / {form_total}')
    total_count_row_parts.append(f'{overall_quantum} / {overall_total}')
    latex_content.append(' & '.join(total_count_row_parts) + ' \\\\')
    total_percentage_row_parts = ['']
    for comment_form in comment_forms:
        form_total = 0
        form_quantum = 0
        for entity_type in ['function', 'class', 'module']:
            if comment_form in entities[entity_type]:
                form_total += entities[entity_type][comment_form]['total_count']
                form_quantum += entities[entity_type][comment_form]['quantum_count']
        form_percentage = round(form_quantum / form_total * 100, 2) if form_total > 0 else 0.0
        total_percentage_row_parts.append(f'({form_percentage:.2f}\\%)')
    overall_percentage = round(overall_quantum / overall_total * 100, 2) if overall_total > 0 else 0.0
    total_percentage_row_parts.append(f'({overall_percentage:.2f}\\%)')
    latex_content.append(' & '.join(total_percentage_row_parts) + ' \\\\')
    latex_content.append('\\hline')
    latex_content.append('\\end{tabular}')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(latex_content))
    print(f'LaTeX table generated: {output_file}')
    print('\nGenerated LaTeX table:')
    print('\n'.join(latex_content))

def main():
    json_file = 'rqs/distribution_based/results/rq4_quantum_proportion.json'
    output_file = 'rqs/distribution_based/table/rq4_quantum_proportion_table.tex'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.exists(json_file):
        print(f'Error: Input file not found: {json_file}')
        return
    print(f'Loading data from {json_file}...')
    data = load_rq4_data(json_file)
    print('Aggregating data by entity type...')
    entities = aggregate_by_entity(data)
    print('Generating LaTeX table...')
    generate_latex_table(entities, output_file)
    print('\nRQ4 LaTeX table generation complete!')
if __name__ == '__main__':
    main()
