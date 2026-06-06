# TODO: Break into smaller files?

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

    start: lines=line+ { (lines, LOCATIONS) }
    line: e1=e a=item e2=e b=item e3=e newline { (e1, a, e2, b, e3, newline, LOCATIONS) }
    item: "a" { LOCATIONS }
    e: { LOCATIONS }
    newline: "\n" { LOCATIONS }
    """)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert parser.from_text("aa\naa\n", verbose_stream=sys.stdout).start() == (
        [ # lines (= line+)
            (
                ((0, 0), (0, 0)), # e1
                ((0, 0), (0, 1)), # a
                ((0, 1), (0, 1)), # e2
                ((0, 1), (0, 2)), # b
                ((0, 2), (0, 2)), # e3
                ((0, 2), (1, 0)), # newline
                                  # (see "`CharBasedParser`'s design
                                  # of match locations behavior of `\n`"
                                  # in miscellanous.rst)
                ((0, 0), (1, 0)), # line
            ),
            (
                ((1, 0), (1, 0)), # e1
                ((1, 0), (1, 1)), # a
                ((1, 1), (1, 1)), # e2
                ((1, 1), (1, 2)), # b
                ((1, 2), (1, 2)), # e3
                ((1, 2), (2, 0)), # newline
                ((1, 0), (2, 0)), # line
            ),
        ],
        ((0, 0), (2, 0)) # start
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