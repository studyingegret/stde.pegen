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
        # It is easier this way to process later (for example, move all locations/elements
        # 3 characters to the right). (XXX: on second thoughts, is it really so?
        # But it does reflect the source more accurately(?))
        # (This is different from DefaultParser;
        # see also the comment in tests.v2.test_parsing.test_locations)
        ((0, 0), (3, 0))
        # On second thoughts it might be better to let \n
        # be the last character on a line
        # instead of jumping to the next line within itself
        #
        # The only advantage I can think (guess) of for the current behavior
        # is that it proves that tokens are "consecutive"
        # (next token's start is this token's end)
        # But I can't remember where this property is taken advanage of
        #
        # (TODO)
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