from typing import Optional

from stde.pegen.common import ValidationError
from stde.pegen.v2.grammar import Alt, GrammarVisitor, Rhs, Rule, Grammar


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
                f"In {self.rulename} there is an alternative that will "
                f"never be visited:\n{second_alt}\n"
                f"(note: {first_alt} will match instead)"
            )


def check_unreachable_rules(grammar: Grammar) -> None: #...
    checker = _UnreachableRuleChecker(grammar)
    for rule_name, rule in grammar.rules.items():
        checker.validate_rule(rule_name, rule)
