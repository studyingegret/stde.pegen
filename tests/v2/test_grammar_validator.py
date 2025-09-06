import pytest
from textwrap import dedent
from stde.pegen.grammar_v2 import Grammar
from stde.pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from stde.pegen.parser_v2 import FAILURE
from stde.pegen.validator_v2 import SubRuleValidator, ValidationError


def test_rule_with_no_collision() -> None:
    grammar_source = dedent("""
    start: bad_rule
    sum:
        | NAME '-' NAME
        | NAME '+' NAME
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert grammar is not FAILURE
    validator = SubRuleValidator(grammar)
    for rule_name, rule in grammar.rules.items():
        validator.validate_rule(rule_name, rule)

def test_rule_with_simple_collision() -> None:
    grammar_source = dedent("""
    start: bad_rule
    sum:
        | NAME '+' NAME
        | NAME '+' NAME ';'
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert grammar is not FAILURE
    validator = SubRuleValidator(grammar)
    with pytest.raises(ValidationError):
        for rule_name, rule in grammar.rules.items():
            validator.validate_rule(rule_name, rule)

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
    assert grammar is not FAILURE
    validator = SubRuleValidator(grammar)
    with pytest.raises(ValidationError):
        for rule_name, rule in grammar.rules.items():
            validator.validate_rule(rule_name, rule)
