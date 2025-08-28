import sys
from pathlib import Path
from textwrap import dedent

from stde.pegen.parser_v2 import FAILURE
from stde.pegen.build_v2 import generate_code_from_grammar, generate_parser_from_grammar, load_grammar_from_string

# To debug a parser run, add `verbose_stream=sys.stdout` in `from_text`
# and view "Captured stdout call" in pytest output

def test_not_whitespace_tokenized() -> None:
    grammar = dedent("""
        @base "CharBasedParser"

        start: ("a" | "b")+ $
    """)
    #with open(Path(__file__).parent / "../../t/output1.txt", "w") as f:
    #    generate_code_from_grammar(load_grammar_from_string(grammar).grammar, output_file=f)
    parser = generate_parser_from_grammar(grammar).parser_class
    #TODO: Change interface to return error information?
    assert parser.from_text("").start() == FAILURE
    assert parser.from_text("aba").start() == ["a", "b", "a"]
    assert parser.from_text(" ").start() == FAILURE
    assert parser.from_text("a b").start() == FAILURE

def test_locations() -> None:
    grammar = dedent("""
        @base "CharBasedParser"
        @location_format "(start, end)"

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
    assert parser.from_text("").start() == FAILURE
    assert parser.from_text("a,b,a").start() == ([
        ("a", ((0, 0), (0, 1))),
        ("b", ((0, 2), (0, 3))),
        ("a", ((0, 4), (0, 5))),
    ], ((0, 0), (0, 5)))
    assert parser.from_text(" ").start() == FAILURE
    assert parser.from_text("a, b").start() == FAILURE