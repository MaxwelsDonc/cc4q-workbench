#!/usr/bin/env python3

import json
import os

def load_rq1_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['combination_distribution']

def aggregate_by_entity(data):
    entities = {'function': {}, 'class': {}, 'module': {}}
    for key, value in data.items():
        entity_type = value['code_entity']
        comment_form = value['comment_forms']
        count = value['count']
        percentage = value['percentage']
        if entity_type in entities:
            entities[entity_type][comment_form] = {'count': count, 'percentage': percentage}
    return entities

def calculate_totals(entities):
    totals = {}
    overall_total = 0
    for entity_type, comments in entities.items():
        entity_total = sum((data['count'] for data in comments.values()))
        totals[entity_type] = entity_total
        overall_total += entity_total
    return (totals, overall_total)

def generate_latex_table(entities, output_file):
    totals, overall_total = calculate_totals(entities)
    entity_names = {'function': 'Functions', 'class': 'Classes', 'module': 'Modules'}
    comment_forms = ['docstring', 'block', 'inline']
    latex_content = []
    latex_content.append('\\begin{tabular}{lcccc}')
    latex_content.append('\\hline')
    latex_content.append('\\textbf{Entity Type} & \\textbf{Docstring} & \\textbf{Block Comments} & \\textbf{Inline Comments} & \\textbf{Total Comments} \\\\')
    latex_content.append('\\hline')
    for entity_type in ['function', 'class', 'module']:
        entity_data = entities[entity_type]
        entity_name = entity_names[entity_type]
        entity_total = totals[entity_type]
        row_parts = [f'\\textbf{{{entity_name}}}']
        for comment_form in comment_forms:
            if comment_form in entity_data:
                count = entity_data[comment_form]['count']
                percentage = entity_data[comment_form]['percentage']
                row_parts.append(f'{count} ({percentage}\\%)')
            else:
                row_parts.append('0 (0\\%)')
        entity_percentage = round(entity_total / overall_total * 100, 1)
        row_parts.append(f'{entity_total} ({entity_percentage}\\%)')
        latex_content.append(' & '.join(row_parts) + ' \\\\')
        latex_content.append('')
    total_row_parts = ['\\textbf{Total}']
    for comment_form in comment_forms:
        form_total = 0
        for entity_type in ['function', 'class', 'module']:
            if comment_form in entities[entity_type]:
                form_total += entities[entity_type][comment_form]['count']
        form_percentage = round(form_total / overall_total * 100, 2)
        total_row_parts.append(f'{form_total} ({form_percentage}\\%)')
    total_row_parts.append(f'{overall_total} (100\\%)')
    latex_content.append(' & '.join(total_row_parts) + ' \\\\')
    latex_content.append('\\hline')
    latex_content.append('\\end{tabular}')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(latex_content))
    print(f'LaTeX table generated: {output_file}')
    print('\nGenerated LaTeX table:')
    print('\n'.join(latex_content))

def main():
    json_file = 'rqs/distribution_based/results/rq1_distribution.json'
    output_file = 'rqs/distribution_based/table/rq1_generated_table.tex'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if not os.path.exists(json_file):
        print(f'Error: Input file not found: {json_file}')
        return
    print(f'Loading data from {json_file}...')
    data = load_rq1_data(json_file)
    print('Aggregating data by entity type...')
    entities = aggregate_by_entity(data)
    print('Generating LaTeX table...')
    generate_latex_table(entities, output_file)
    print('\nRQ1 LaTeX table generation complete!')
if __name__ == '__main__':
    main()
