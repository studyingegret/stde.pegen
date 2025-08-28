import sys
from textwrap import dedent
from stde.pegen.build_v2 import generate_parser_from_grammar


def test_1() -> None:
    grammar = dedent(r'''
    @base CharBasedParser

    start: s "c" $ { True }
    s: ("a" | "b")*
    ''')
    p = generate_parser_from_grammar(grammar)
    print(p.parser_code)
    parser_class = p.parser_class

    assert parser_class.from_text("ababc").start() is True
    assert parser_class.from_text("c", verbose_stream=sys.stdout).start() is True

def test_2() -> None:
    grammar = dedent(r'''
    @base CharBasedParser

    start: s "c" s $ { True }
    s: ("a" | "b")*
    ''')
    p = generate_parser_from_grammar(grammar)
    print(p.parser_code)
    parser_class = p.parser_class

    assert parser_class.from_text("abcba").start() is True
    assert parser_class.from_text("c", verbose_stream=sys.stdout).start() is True