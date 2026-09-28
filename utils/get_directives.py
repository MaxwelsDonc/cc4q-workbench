import json
import re

def extract_directives_and_roles_from_docstrings(pairs):
    directive_pattern = re.compile('^\\s*\\.\\.\\s+([a-zA-Z0-9_-]+)::', re.MULTILINE)
    role_pattern = re.compile(':([a-zA-Z0-9_-]+):`')
    all_directives = set()
    all_roles = set()
    for pair in pairs:
        if pair.get('comment_type') == 'docstring':
            doc = pair.get('comment_text', '')
            all_directives.update(directive_pattern.findall(doc))
            all_roles.update(role_pattern.findall(doc))
    return (all_directives, all_roles)
if __name__ == '__main__':
    with open('data/output/qiskit/comment_pairs.json', 'r', encoding='utf-8') as f:
        comment_pairs = json.load(f)
    directives, roles = extract_directives_and_roles_from_docstrings(comment_pairs)
    print('🎯 Directives found:')
    for d in sorted(directives):
        print(f'  - {d}')
    print('\n🎯 Roles found:')
    for r in sorted(roles):
        print(f'  - {r}')
