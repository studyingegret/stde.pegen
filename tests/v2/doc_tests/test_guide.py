import sys
import token
from textwrap import dedent
from tokenize import TokenInfo

from stde.pegen.v2.parser import FAILURE, ParseFailure
import pytest
from stde.pegen.v2.build import generate_parser_from_grammar

def test_beginning() -> None:
    grammar = dedent('''
    start: a=NUMBER "+" b=NUMBER NEWLINE $
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    parser = parser_class.from_text("1 + 2")
    assert parser.start() == [
        TokenInfo(token.NUMBER, "1", (1, 0), (1, 1), "1 + 2"),
        TokenInfo(token.OP, "+", (1, 2), (1, 3), "1 + 2"),
        TokenInfo(token.NUMBER, "2", (1, 4), (1, 5), "1 + 2"),
        TokenInfo(token.NEWLINE, "", (1, 5), (1, 6), "1 + 2")
    ]

    parser = parser_class.from_text("1 + a")
    result = parser.start()
    assert isinstance(result, ParseFailure)
    exc = parser.make_syntax_error("Cannot parse expression", "some name")
    assert "Cannot parse expression" in str(exc)
    assert exc.filename == "some name"
    assert exc.lineno == 1
    assert exc.offset == 5

def test_with_actions() -> None:
    grammar = dedent('''
    start: a=NUMBER "+" b=NUMBER NEWLINE $ { int(a.string) + int(b.string) }
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("1 + 2").start() == 3
    assert isinstance(parser_class.from_text("1 + a").start(), ParseFailure)

def test_with_subtraction() -> None:
    grammar = dedent('''
    start:
        | a=NUMBER "+" b=NUMBER NEWLINE $ { int(a.string) + int(b.string) }
        | a=NUMBER "-" b=NUMBER NEWLINE $ { int(a.string) - int(b.string) }
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("3 + 4").start() == 7
    assert parser_class.from_text("5 - 10").start() == -5

# Note: The section "Compound expressions"'s example code isn't tested yet.

def test_compound_and_with_multiplicative() -> None:
    grammar = dedent('''
    start: expr NEWLINE $ { expr }

    expr:
        | a=expr2 "+" b=expr { a + b }
        | a=expr2 "-" b=expr { a - b }
        | expr2

    expr2:
        | a=expr2 "*" b=NUMBER { a * int(b.string) }
        | a=expr2 "/" b=NUMBER { a / int(b.string) }
        | NUMBER { int(number.string) }
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class

    # Note: no input is originally in the guide
    assert parser_class.from_text("42").start() == 42
    assert parser_class.from_text("1 + 2").start() == 3
    assert parser_class.from_text("1 + 2 * 3").start() == 7
    assert parser_class.from_text("8 / 2 * 3").start() == 12

# Note: there is no input for this in the guide
def test_parser_with_header() -> None:
    grammar = dedent('''
    @header """
    def token_to_int(t):
        return int(t.string)
    """

    start: expr NEWLINE $ { expr }

    expr:
        | a=expr2 "+" b=expr { a + b }
        | a=expr2 "-" b=expr { a - b }
        | expr2

    expr2:
        | a=expr2 "*" b=NUMBER { a * token_to_int(b) }
        | a=expr2 "/" b=NUMBER { a / token_to_int(b) }
        | NUMBER { token_to_int(number) }
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("3 * 4 + 5").start() == 17
    assert parser_class.from_text("20 / 4 - 2").start() == 3

def test_color_parsing_char_based() -> None:
    grammar = dedent('''
    @base CharBasedParser

    start: "#" r=field g=field b=field a=field $ { (r, g, b, a) }
         | "#" r=field g=field b=field $ { (r, g, b, 255) }

    field: a=char b=char { int(a + b, 16) }
    char: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
        | "a" | "b" | "c" | "d" | "e" | "f"
        | "A" | "B" | "C" | "D" | "E" | "F"
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("#1f1e33").start() == (31, 30, 51, 255)
    assert parser_class.from_text("#002134aa").start() == (0, 33, 52, 170)
    assert isinstance(parser_class.from_text("#0021 34aa").start(), ParseFailure)
    assert isinstance(parser_class.from_text("#e0e1ccull").start(), ParseFailure)

@pytest.mark.xfail
def test_color_parsing_with_default_parser() -> None:
    grammar = dedent('''
    start: "#" r=field g=field b=field a=field $ { (r, g, b, a) }
         | "#" r=field g=field b=field $ { (r, g, b, 255) }

    field: a=char b=char { int(a + b, 16) }
    char: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
        | "a" | "b" | "c" | "d" | "e" | "f"
        | "A" | "B" | "C" | "D" | "E" | "F"
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("#ff33cc").start() == (255, 51, 204, 255)
    assert parser_class.from_text("#002134aa").start() == (0, 33, 52, 170)
    assert isinstance(parser_class.from_text("# 002134aa").start(), ParseFailure)

# Note: there is no input for this in the guide
def test_compound_and_with_multiplicative_char_based() -> None:
    grammar = dedent(r'''
    @base CharBasedParser

    start: s expr s $ { expr }

    expr:
        | a=expr2 s "+" s b=expr { a + b }
        | a=expr2 s "-" s b=expr { a - b }
        | expr2

    expr2:
        | a=expr2 s "*" s b=number { a * b }
        | a=expr2 s "/" s b=number { a / b }
        | number

    number:
        digits=digit+ { int("".join(digits)) }

    digit:
        "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"

    s:
        (" " | "\t")*
    ''')
    p = generate_parser_from_grammar(grammar, parser_verbose_stream=sys.stdout)
    #print(p.parser_code)
    parser_class = p.parser_class
    assert parser_class.from_text("42").start() == 42
    assert parser_class.from_text("1 + 2").start() == 3
    assert parser_class.from_text("1 + 2 * 3").start() == 7
    assert parser_class.from_text("8 / 2 * 3").start() == 12
