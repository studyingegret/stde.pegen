import sys
from pathlib import Path
from textwrap import dedent

from stde.pegen.v2.parser import ParseFailure
from stde.pegen.v2.build import generate_code_from_grammar, generate_parser_from_grammar, load_grammar_from_string

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
    assert isinstance(parser.from_text("").start(), ParseFailure)
    assert parser.from_text("aba").start() == ["a", "b", "a"]
    assert isinstance(parser.from_text(" ").start(), ParseFailure)
    assert isinstance(parser.from_text("a b").start(), ParseFailure)

def test_locations() -> None:
    grammar = dedent(r"""
    @base "CharBasedParser"
    @location_format "(start, end)"

    start: items=sep.item+ sep? $ { (items, LOCATIONS) }
    item: "a" { LOCATIONS }
    sep: (" "|"\n")* "," (" "|"\n")*
    """)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert parser.from_text("a,   a  ,a,", verbose_stream=sys.stdout).start() == ([
        # End position is "one character after".
        ((0, 0), (0, 1)),
        ((0, 5), (0, 6)),
        ((0, 9), (0, 10)),
    ], ((0, 0), (0, 11)))
    #XXX: Should port this check to DefaultParser test?
    assert parser.from_text("a,\na,\n  a,a,\n", verbose_stream=sys.stdout).start() == (
        [
            ((0, 0), (0, 1)),
            ((1, 0), (1, 1)),
            ((2, 2), (2, 3)),
            ((2, 4), (2, 5)),
        ],
        # Note: Ending with a "\n" pushes the end position onto the next line.
        # It is easier this way to process later (for example, move all locations
        # 3 characters to the right).
        ((0, 0), (3, 0))
    )

def test_null_locations() -> None:
    grammar = dedent("""
    @base "CharBasedParser"
    @location_format "(start, end)"
    start: $ { LOCATIONS }
    """)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert parser.from_text("", verbose_stream=sys.stdout).start() == ((0, 0), (0, 0))

def test_sample_1() -> None:
    grammar = dedent("""
    @base "CharBasedParser"
    @location_format "(start, end)"

    start: parens_contents $
    parens_contents: items=sep.item+ sep?
    item: "a"
    sep: " "* "," " "*
    """)
    #print(generate_code_from_grammar(load_grammar_from_string(grammar).grammar).parser_code)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert isinstance(parser.from_text("").start(), ParseFailure)
    assert isinstance(parser.from_text(" ").start(), ParseFailure)
    assert isinstance(parser.from_text("a, b").start(), ParseFailure)