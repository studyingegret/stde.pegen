from textwrap import dedent
from pegen.build_v2 import generate_code_from_grammar, generate_parser_from_grammar, load_grammar_from_string
import pytest

def test_not_whitespace_tokenized() -> None:
    grammar = dedent("""
        @base "CharBasedParser"

        start: ("a" | "b")+
    """)
    print(generate_code_from_grammar(load_grammar_from_string(grammar).grammar).parser_code)
    parser = generate_parser_from_grammar(grammar).parser_class
    with pytest.raises(SyntaxError):
        parser.from_text("").start()
    parser.from_text("aba").start()
    with pytest.raises(SyntaxError):
        parser.from_text(" ").start()
    with pytest.raises(SyntaxError):
        parser.from_text("a b").start()

def test_locations() -> None:
    grammar = dedent("""
        @base "CharBasedParser"
        @locations_expand "(start, end)"

        start: parens_contents
        parens_contents: items=",".item+ [","] { (items, LOCATIONS) }
        item:
            | "a" { ("a", LOCATIONS) }
            | "b" { ("b", LOCATIONS) }
            | "(" parens_contents ")" { (parens_contents, LOCATIONS) }
    """)
    print(generate_code_from_grammar(load_grammar_from_string(grammar).grammar).parser_code)
    parser = generate_parser_from_grammar(grammar).parser_class
    with pytest.raises(SyntaxError):
        parser.from_text("").start()
    parser.from_text("aba").start()
    with pytest.raises(SyntaxError):
        parser.from_text(" ").start()
    with pytest.raises(SyntaxError):
        parser.from_text("a b").start()