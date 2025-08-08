import pytest
from textwrap import dedent
from pegen.build_v2 import generate_parser_from_grammar

def test_1() -> None:
    grammar = dedent('''
    start: "!" "="
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("!=").start() is None

def test_2() -> None:
    grammar = dedent('''
    start: '"' | STRING
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("!=").start() is None