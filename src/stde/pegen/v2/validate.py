from contextlib import contextmanager
from typing import Dict, Iterator, Optional, Set

from stde.pegen.common import ValidationError
from stde.pegen.v2.grammar import Alt, GrammarItem, GrammarVisitor, NameLeaf, Rhs, Rule, Grammar, TopLevelItem


class _UnreachableRuleChecker(GrammarVisitor):
    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.rulename: Optional[str] = None

    def validate_rule(self, rulename: str, node: Rule) -> None:
        self.rulename = rulename
        self.visit(node)
        self.rulename = None

    def visit_Rhs(self, node: Rhs) -> None:
        for index, alt in enumerate(node.alts):
            for other_alt in node.alts[index+1:]:
                self.check_intersection(alt, other_alt)

    def check_intersection(self, first_alt: Alt, second_alt: Alt) -> None:
        if str(second_alt).startswith(str(first_alt)):
            raise ValidationError(
                f"In rule {self.rulename}: The branch \n    {second_alt}\nwill "
                f"never be visited because\n    "
                f"{first_alt}\nwill match before it is tried"
            )


def check_unreachable_rules(grammar: Grammar) -> None:
    checker = _UnreachableRuleChecker(grammar)
    for rule_name, rule in grammar.rules.items():
        checker.validate_rule(rule_name, rule)


class _CheckingVisitor(GrammarVisitor):
    def __init__(self, items: Dict[str, GrammarItem], extra_names: Set[str]):
        self.items = items
        self.extra_names = extra_names
        self._in_rule: str = "(?)"

    @contextmanager
    def in_rule(self, name: str) -> Iterator[None]:
        assert self._in_rule == "(?)"
        self._in_rule = name
        try:
            yield
        finally:
            self._in_rule = "(?)"

    def validation_error(self, msg: str) -> ValidationError:
        assert self._in_rule != "(?)"
        return ValidationError(f"In rule {self._in_rule}: {msg}")

    def visit_Rule(self, rule: Rule) -> None:
        if rule.name.startswith("_"):
            raise ValidationError(f"Rule {rule.name}: Name cannot start with underscore")
        with self.in_rule(rule.name):
            self.visit(rule.rhs)

    def visit_NameLeaf(self, node: NameLeaf) -> None:
        if node.value not in self.items and node.value not in self.extra_names:
            # TODO: Add line/col info to (leaf) nodes
            raise self.validation_error(f"'{node.value}': Unknown name in syntax")

    def visit_TopLevelItem(self, node: TopLevelItem) -> None:
        if node.name and node.name.startswith("_"):
            raise self.validation_error(f"capture variable '{node.name}': Name cannot start with underscore")
        self.visit(node.item)

    def visit_ExternDecl(self, node: TopLevelItem) -> None:
        if node.name and node.name.startswith("_"):
            raise ValidationError(f"Extern declaration {node.name}: "
                                  "Name cannot start with underscore")

def basic_check(grammar: Grammar, extra_names: Set[str]) -> None:
    checker = _CheckingVisitor(grammar.items, extra_names or set())
    checker.visit(grammar.items.values())