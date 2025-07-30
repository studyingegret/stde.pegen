import sys
from pathlib import Path
from textwrap import dedent
from pegen.build_v2 import generate_code_from_grammar, generate_parser_from_grammar, load_grammar_from_string

def test_not_whitespace_tokenized() -> None:
    grammar = dedent("""
        @base "CharBasedParser"

        start: ("a" | "b")+ $
    """)
    with open(Path(__file__).parent / "../../t/output1.txt", "w") as f:
        generate_code_from_grammar(load_grammar_from_string(grammar).grammar, output_file=f)
    parser = generate_parser_from_grammar(grammar).parser_class
    #TODO: Change interface to return error information?
    assert parser.from_text("").start() is None
    assert parser.from_text("aba").start() == ["a", "b", "a"]
    assert parser.from_text(" ").start() is None
    assert parser.from_text("a b", verbose_stream=sys.stdout).start() is None

def test_locations() -> None:
    grammar = dedent("""
        @base "CharBasedParser"
        @locations_format "(start, end)"

        start: parens_contents $
        parens_contents: items=",".item+ [","] { (items, LOCATIONS) }
        item:
            | "a" { ("a", LOCATIONS) }
            | "b" { ("b", LOCATIONS) }
            | "(" parens_contents ")" { (parens_contents, LOCATIONS) }
    """)
    #print(generate_code_from_grammar(load_grammar_from_string(grammar).grammar).parser_code)
    parser = generate_parser_from_grammar(grammar).parser_class
    #TODO
    assert parser.from_text("").start() is None
    parser.from_text("aba").start() #TODO
    assert parser.from_text(" ").start() is None
    assert parser.from_text("a b").start() is None