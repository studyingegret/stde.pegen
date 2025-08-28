import pytest

from stde.pegen.grammar_v2 import Grammar
from stde.pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from stde.pegen.utils_v2 import parse_string
from stde.pegen.validator_v2 import SubRuleValidator, ValidationError


def test_rule_with_no_collision() -> None:
    grammar_source = """
    start: bad_rule
    sum:
        | NAME '-' NAME
        | NAME '+' NAME
    """
    grammar: Grammar = parse_string(grammar_source, GrammarParser)
    validator = SubRuleValidator(grammar)
    for rule_name, rule in grammar.rules.items():
        validator.validate_rule(rule_name, rule)

def test_rule_with_simple_collision() -> None:
    grammar_source = """
    start: bad_rule
    sum:
        | NAME '+' NAME
        | NAME '+' NAME ';'
    """
    grammar: Grammar = parse_string(grammar_source, GrammarParser)
    validator = SubRuleValidator(grammar)
    with pytest.raises(ValidationError):
        for rule_name, rule in grammar.rules.items():
            validator.validate_rule(rule_name, rule)

def test_rule_with_collision_after_some_other_rules() -> None:
    grammar_source = """
    start: bad_rule
    sum:
        | NAME '+' NAME
        | NAME '*' NAME ';'
        | NAME '-' NAME
        | NAME '+' NAME ';'
    """
    grammar: Grammar = parse_string(grammar_source, GrammarParser)
    validator = SubRuleValidator(grammar)
    with pytest.raises(ValidationError):
        for rule_name, rule in grammar.rules.items():
            validator.validate_rule(rule_name, rule)
