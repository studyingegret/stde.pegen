import token
from textwrap import dedent
from tokenize import TokenInfo
from pegen.build_v2 import generate_parser_from_grammar

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
    assert result is None
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
    parser = parser_class.from_text("1 + 2")
    assert parser.start() == 3
    parser = parser_class.from_text("1 + a")
    assert parser.start() is None

def test_with_subtraction() -> None:
    grammar = dedent('''
    start:
        | a=NUMBER "+" b=NUMBER NEWLINE $ { int(a.string) + int(b.string) }
        | a=NUMBER "-" b=NUMBER NEWLINE $ { int(a.string) - int(b.string) }
    ''')
    parser_class = generate_parser_from_grammar(grammar).parser_class

    parser = parser_class.from_text("3 + 4")
    assert parser.start() == 7

    parser = parser_class.from_text("5 - 10")
    assert parser.start() == -5

def test_compound_expressions() -> None:
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

    parser = parser_class.from_text("42")
    assert parser.start() == 42

    parser = parser_class.from_text("1 + 2")
    assert parser.start() == 3

    parser = parser_class.from_text("1 + 2 * 3")
    assert parser.start() == 7  # 1 + (2 * 3) = 7

    parser = parser_class.from_text("8 / 2 * 3")
    assert parser.start() == 12  # (8/2)*3 = 12

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

    # Note: no input is originally in the guide

    parser = parser_class.from_text("3 * 4 + 5")
    assert parser.start() == 17

    parser = parser_class.from_text("20 / 4 - 2")
    assert parser.start() == 3
