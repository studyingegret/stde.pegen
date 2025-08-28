from typing import Any

from stde.pegen.grammar_v2 import GrammarVisitor
from stde.pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from stde.pegen.utils_v2 import parse_string


class Visitor(GrammarVisitor):
    def __init__(self) -> None:
        self.n_nodes = 0

    def visit(self, node: Any, *args: Any, **kwargs: Any) -> None:
        self.n_nodes += 1
        super().visit(node, *args, **kwargs)


def test_parse_trivial_grammar() -> None:
    grammar = """
    start: 'a'
    """
    rules = parse_string(grammar, GrammarParser)
    visitor = Visitor()

    visitor.visit(rules)

    assert visitor.n_nodes == 6


def test_parse_or_grammar() -> None:
    grammar = """
    start: rule
    rule: 'a' | 'b'
    """
    rules = parse_string(grammar, GrammarParser)
    visitor = Visitor()

    visitor.visit(rules)

    # Grammar/Rule/Rhs/Alt/TopLevelItem/NameLeaf   -> 6
    #         Rule/Rhs/                            -> 2
    #                  Alt/TopLevelItem/StringLeaf -> 3
    #                  Alt/TopLevelItem/StringLeaf -> 3

    assert visitor.n_nodes == 14


def test_parse_repeat1_grammar() -> None:
    grammar = """
    start: 'a'+
    """
    rules = parse_string(grammar, GrammarParser)
    visitor = Visitor()

    visitor.visit(rules)

    # Grammar/Rule/Rhs/Alt/TopLevelItem/Repeat1/StringLeaf -> 6
    assert visitor.n_nodes == 7


def test_parse_repeat0_grammar() -> None:
    grammar = """
    start: 'a'*
    """
    rules = parse_string(grammar, GrammarParser)
    visitor = Visitor()

    visitor.visit(rules)

    # Grammar/Rule/Rhs/Alt/TopLevelItem/Repeat0/StringLeaf -> 6

    assert visitor.n_nodes == 7


def test_parse_optional_grammar() -> None:
    grammar = """
    start: 'a' ['b']
    """
    rules = parse_string(grammar, GrammarParser)
    visitor = Visitor()

    visitor.visit(rules)

    # Grammar/Rule/Rhs/Alt/TopLevelItem/StringLeaf                                -> 6
    #                      TopLevelItem/Opt/Group/Rhs/Alt/TopLevelItem/Stringleaf -> 7

    print(repr(rules))
    assert visitor.n_nodes == 13
