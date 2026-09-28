#!/usr/bin/env python3

import re
import textwrap
import warnings
from typing import List, Dict, Any
import spacy
from docutils import nodes
from docutils.core import publish_doctree
from docutils.parsers.rst import Directive, directives, roles
from docutils.parsers.rst.directives.admonitions import Attention, Caution, Danger, Error, Hint, Important, Note, Warning
from docutils.parsers.rst.directives.body import ParsedLiteral, Rubric
from docutils.parsers.rst.directives.images import Image
from sphinx.directives.code import CodeBlock
from sphinx.directives.patches import MathDirective
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    try:
        nlp = spacy.load('en_core_web_md')
    except OSError:
        try:
            nlp = spacy.load('en_core_web_lg')
        except OSError:
            nlp = None
            print('Warning: 无法加载 spaCy 英文模型，paragraph 分割功能将被禁用')

def dummy_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    return ([nodes.literal(text, text)], [])

class DummyDirective(Directive):
    has_content = True
    optional_arguments = 10
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        node = nodes.container()
        node['directive_name'] = self.name
        node['directive_content'] = self.block_text
        return [node]

class DummyPlotDirective(Directive):
    has_content = True
    option_spec = {'alt': directives.unchanged, 'include-source': directives.flag, 'width': directives.length_or_percentage_or_unitless, 'height': directives.length_or_unitless, 'scale': directives.percentage, 'align': lambda x: directives.choice(x, ('left', 'center', 'right')), 'class': directives.class_option, 'caption': directives.unchanged, 'context': directives.flag, 'nofigs': directives.flag, 'encoding': directives.encoding}

    def run(self):
        code = '\n'.join(self.content)
        literal = nodes.literal_block(code, code)
        literal['language'] = 'python'
        return [literal]

def register_all_known_sphinx_rst_support():
    role_names = ['Class', 'attr', 'class', 'code', 'data', 'exc', 'func', 'math', 'meth', 'method', 'mod', 'obj', 'ref']
    for role_name in role_names:
        roles.register_local_role(role_name, dummy_role)
    directives.register_directive('note', Note)
    directives.register_directive('warning', Warning)
    directives.register_directive('hint', Hint)
    directives.register_directive('attention', Attention)
    directives.register_directive('important', Important)
    directives.register_directive('caution', Caution)
    directives.register_directive('danger', Danger)
    directives.register_directive('error', Error)
    directives.register_directive('code-block', CodeBlock)
    directives.register_directive('parsed-literal', ParsedLiteral)
    directives.register_directive('image', Image)
    directives.register_directive('rubric', Rubric)
    directives.register_directive('math', MathDirective)
    directives.register_directive('plot', DummyPlotDirective)
    sphinx_directives = ['autoattribute', 'autoclass', 'autodata', 'autoexception', 'autofunction', 'automethod', 'automodule', 'autosummary', 'list-table', 'versionadded', 'versionchanged', 'deprecated', 'currentmodule', 'data', 'seealso', 'code', 'py:data']
    for name in sphinx_directives:
        directives.register_directive(name, DummyDirective)
BLOCK_TYPE_MAP = {'paragraph': 'paragraph', 'literal_block': 'code', 'doctest_block': 'code', 'note': 'note', 'warning': 'note', 'hint': 'note', 'admonition': 'note', 'section': 'section', 'title': 'title', 'definition_list': 'args', 'field_list': 'params', 'bullet_list': 'list', 'enumerated_list': 'list', 'rubric': 'title', 'block_quote': 'quote'}
SKIP_TYPES = {'system_message', 'raw', 'target', 'substitution_definition'}

def get_block_type(node):
    return BLOCK_TYPE_MAP.get(node.__class__.__name__, 'unknown')

def segment_paragraph_with_spacy(text: str) -> List[str]:
    if not nlp or not text.strip():
        return [text.strip()] if text.strip() else []
    try:
        doc = nlp(text.strip())
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        return sentences if sentences else [text.strip()]
    except Exception:
        return [text.strip()]

def process_definition_list(node) -> List[Dict[str, Any]]:
    blocks = []
    for item in node:
        term = item[0].astext()
        definition = item[1].astext()
        blocks.append({'type': term, 'desc': definition, 'content': f'{term}: {definition}'})
    return blocks

def process_field_list(node) -> List[Dict[str, Any]]:
    blocks = []
    for field in node:
        name = field[0].astext()
        desc = field[1].astext()
        blocks.append({'type': name, 'desc': desc, 'content': f'{name}: {desc}'})
    return blocks

def process_list(node) -> List[Dict[str, Any]]:
    blocks = []
    for item in node:
        blocks.append({'type': 'list_item', 'content': item.astext()})
    return blocks

def process_admonition(node) -> Dict[str, Any]:
    title_node = node.next_node(nodes.title)
    title = title_node.astext() if title_node else ''
    content = '\n'.join((child.astext() for child in node.children if child != title_node))
    return {'type': 'note', 'title': title, 'content': content}

def process_section(node) -> List[Dict[str, Any]]:
    blocks = []
    title_node = node.next_node(nodes.title)
    title = title_node.astext() if title_node else ''
    blocks.append({'type': 'section', 'title': title, 'content': title})
    for child in node.children:
        if child != title_node:
            child_typename = child.__class__.__name__
            if child_typename in SKIP_TYPES:
                continue
            if isinstance(child, nodes.paragraph):
                sentences = segment_paragraph_with_spacy(child.astext())
                for sentence in sentences:
                    blocks.append({'type': 'paragraph', 'content': sentence})
            elif isinstance(child, nodes.literal_block):
                blocks.append({'type': 'code', 'content': child.astext()})
            elif isinstance(child, nodes.admonition):
                blocks.append(process_admonition(child))
            elif isinstance(child, nodes.container) and 'directive_name' in child:
                directive_name = child['directive_name']
                directive_content = child['directive_content']
                blocks.append({'type': 'directive', 'name': directive_name, 'content': directive_content})
            else:
                blocks.append({'type': child_typename, 'content': child.astext()})
    return blocks

def process_container(node) -> Dict[str, Any]:
    directive_name = node['directive_name']
    directive_content = node['directive_content']
    return {'type': 'directive', 'name': directive_name, 'content': directive_content}

def segment_docstring(comment_text: str) -> List[Dict[str, Any]]:
    if not comment_text or not comment_text.strip():
        return []
    try:
        register_all_known_sphinx_rst_support()
        docstring = textwrap.dedent(comment_text)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            document = publish_doctree(docstring, settings_overrides={'report_level': 5, 'halt_level': 6, 'warning_stream': None})
        blocks = []
        for node in document.children:
            typename = node.__class__.__name__
            if typename in SKIP_TYPES:
                continue
            if isinstance(node, nodes.definition_list):
                blocks.extend(process_definition_list(node))
            elif isinstance(node, nodes.field_list):
                blocks.extend(process_field_list(node))
            elif isinstance(node, (nodes.bullet_list, nodes.enumerated_list)):
                blocks.extend(process_list(node))
            elif isinstance(node, nodes.admonition):
                blocks.append(process_admonition(node))
            elif isinstance(node, nodes.rubric):
                blocks.append({'type': 'title', 'content': node.astext()})
            elif isinstance(node, nodes.section):
                blocks.extend(process_section(node))
            elif isinstance(node, nodes.container) and 'directive_name' in node:
                blocks.append(process_container(node))
            elif isinstance(node, nodes.paragraph):
                sentences = segment_paragraph_with_spacy(node.astext())
                for sentence in sentences:
                    blocks.append({'type': 'paragraph', 'content': sentence})
            else:
                blocks.append({'type': typename, 'content': node.astext()})
        return blocks
    except Exception as e:
        return [{'type': 'paragraph', 'content': comment_text.strip()}]

def parse_docstring_to_blocks(docstring: str) -> List[Dict[str, Any]]:
    return segment_docstring(docstring)
if __name__ == '__main__':
    test_docstring = '\nBuild a :class:`.Gate` object from a :class:`.QuantumCircuit`.\n\nThe gate is anonymous (not tied to a named quantum register),\nand so can be inserted into another circuit. The gate will\nhave the same string name as the circuit.\n\nArgs:\n    circuit (QuantumCircuit): the input circuit.\n\n    parameter_map (dict): For parameterized circuits, a mapping from\n    parameters in the circuit to parameters to be used in the gate.\n    If None, existing circuit parameters will also parameterize the\n    Gate.\n\n    equivalence_library (EquivalenceLibrary): Optional equivalence library\n    where the converted gate will be registered.\n    label (str): Optional gate label.\n\nRaises:\n    QiskitError: if circuit is non-unitary or if\n    parameter_map is not compatible with circuit\n\nReturn:\n    Gate: a Gate equivalent to the action of the\n    input circuit. Upon decomposition, this gate will\n    yield the components comprising the original circuit.\n'
    blocks = segment_docstring(test_docstring)
    print(f'分割成 {len(blocks)} 个语义块:')
    for i, block in enumerate(blocks, 1):
        if block['type'] == 'directive':
            print(f"{i}. 类型: {block['type']}, 指令名: {block['name']}, 内容: {block['content'][:50]}...")
        else:
            print(f"{i}. 类型: {block['type']}, 内容: {block['content'][:50]}...")
