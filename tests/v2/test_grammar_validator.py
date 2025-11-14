import pytest
from textwrap import dedent
from stde.pegen.v2.grammar_parser import GeneratedParser as GrammarParser
from stde.pegen.v2.parser import ParseFailure
from stde.pegen.v2.validate import check_unreachable_rules, ValidationError


def test_rule_with_no_collision() -> None:
    grammar_source = dedent("""
    start: bad_rule
    sum:
        | NAME '-' NAME
        | NAME '+' NAME
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    check_unreachable_rules(grammar)

def test_rule_with_simple_collision() -> None:
    grammar_source = dedent("""
    start: bad_rule
    sum:
        | NAME '+' NAME
        | NAME '+' NAME ';'
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    with pytest.raises(ValidationError):
        check_unreachable_rules(grammar)

def test_rule_with_collision_after_some_other_rules() -> None:
    grammar_source = dedent("""
    start: bad_rule
    sum:
        | NAME '+' NAME
        | NAME '*' NAME ';'
        | NAME '-' NAME
        | NAME '+' NAME ';'
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    with pytest.raises(ValidationError):
        check_unreachable_rules(grammar)
