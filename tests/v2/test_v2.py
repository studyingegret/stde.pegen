import sys
import token
import traceback

from pegen.parser_v2 import FAILURE
import pytest
from pegen.build_v2 import load_grammar_from_string, generate_parser_from_grammar
from textwrap import dedent
from tokenize import TokenInfo

def test_simple() -> None:
    from pegen.build_v2 import generate_parser_from_grammar
    grammar = dedent('''
    start: NUMBER "+" NUMBER NEWLINE $
    ''')
    p = generate_parser_from_grammar(grammar)
    #print(p.parser_code)
    parser_class = p.parser_class

    res = parser_class.from_text("1 + 2", verbose_stream=sys.stdout).start()
    assert res == [
        TokenInfo(token.NUMBER, "1", (1, 0), (1, 1), "1 + 2"),
        TokenInfo(token.OP, "+", (1, 2), (1, 3), "1 + 2"),
        TokenInfo(token.NUMBER, "2", (1, 4), (1, 5), "1 + 2"),
        TokenInfo(token.NEWLINE, "", (1, 5), (1, 6), "1 + 2"),
    ]
    assert int(res[0].string) + int(res[2].string) == 3 #type:ignore[index]

def test_simple_error() -> None:
    from pegen.build_v2 import generate_parser_from_grammar
    grammar = dedent('''
    start: NUMBER "+" NUMBER NEWLINE $
    ''')
    p = generate_parser_from_grammar(grammar)
    #print(p.parser_code)
    parser_class = p.parser_class

    parser = parser_class.from_text("1 + a", verbose_stream=sys.stdout)
    res = parser.start()
    assert res == FAILURE
    with pytest.raises(SyntaxError) as excinfo:
        e = parser.make_syntax_error("Cannot evaluate expression.")
        print(e)
        raise e
    print("".join(traceback.format_exception(excinfo.value)))


def test_accepted_metas() -> None:
    grammar = dedent("""
        @class Class
        @base Base
        @location_format "(start, end, start_lineno, end_lineno, start_colno, end_colno)"
        @metaheader ""
        @header ""
        @trailer ""
        # There must be at least one rule
        start: $
    """)
    load_grammar_from_string(grammar, parser_verbose_stream=sys.stdout)

def test_one_line_indent() -> None:
    grammar = dedent("""
        start: # Note: NEWLINE added by Python tokenizer
            NAME NEWLINE $ {name}
    """)
    p = generate_parser_from_grammar(grammar)
    #print(p.parser_code)
    assert p.parser_class.from_text("hello", verbose_stream=sys.stdout).start().string == "hello" #type:ignore[union-attr]