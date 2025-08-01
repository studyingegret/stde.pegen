import sys
from pegen.build_v2 import generate_code_from_grammar, load_grammar_from_string
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