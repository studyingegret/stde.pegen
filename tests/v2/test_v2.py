from pegen.build_v2 import generate_code_from_grammar, load_grammar_from_string

def test_accepted_metas() -> None:
    grammar = """
    @class Class
    @base Base
    @location_format "(start, end, start_lineno, end_lineno, start_colno, end_colno)"
    @metaheader ""
    @header ""
    @trailer ""
    """
    load_grammar_from_string(grammar)