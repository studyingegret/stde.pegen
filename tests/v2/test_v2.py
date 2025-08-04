import sys
from pegen.build_v2 import load_grammar_from_string, generate_parser_from_grammar
from textwrap import dedent

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
    print(p.parser_code)
    assert p.parser_class.from_text("hello", verbose_stream=sys.stdout).start().string == "hello"