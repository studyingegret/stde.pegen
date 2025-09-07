import contextlib
from abc import abstractmethod
from typing import Any, AbstractSet, Dict, Iterator, List, Optional, Set, TextIO, Tuple
from io import TextIOBase

from stde.pegen import sccutils
from stde.pegen.legacy.grammar import (
    Alt,
    Cut,
    ExternDecl,
    Forced,
    Gather,
    Grammar,
    ValidationError,
    GrammarItem,
    GrammarVisitor,
    Group,
    Lookahead,
    TopLevelItem,
    NameLeaf,
    Opt,
    Plain,
    Repeat0,
    Repeat1,
    Rhs,
    Rule,
    StringLeaf,
)


class CheckingVisitor(GrammarVisitor):
    def __init__(self, items: Dict[str, GrammarItem], extra_names: Set[str]):
        self.items = items
        self.extra_names = extra_names

    def visit_Rule(self, rule: Rule) -> None:
        if rule.name.startswith("_"):
            raise ValidationError(f"Rule names cannot start with underscore ({rule.name})")
        self.visit(rule.rhs)

    def visit_NameLeaf(self, node: NameLeaf) -> None:
        if node.value not in self.items and node.value not in self.extra_names:
            # TODO: Add line/col info to (leaf) nodes
            raise ValidationError(f"Unknown name {node.value!r}")

    def visit_TopLevelItem(self, node: TopLevelItem) -> None:
        if node.name and node.name.startswith("_"):
            raise ValidationError(f"Variable names cannot start with underscore ({node.name})")
        self.visit(node.item)

    def visit_ExternDecl(self, node: TopLevelItem) -> None:
        if node.name and node.name.startswith("_"):
            raise ValidationError(f"Variable names cannot start with underscore ({node.name})")


def validate_items(items: Dict[str, GrammarItem], tokens: Set[str]) -> None:
    checker = CheckingVisitor(items, tokens)
    checker.visit(items.values())


class ParserGenerator:
    """ParserGenerators should keep the following convention:
    - __init__ should validate the grammar (except for checks
      that can only be done at generation time or checks
      that are too costly to be practical, etc).
    - Potentially costly operations (e.g. downloading a file) should be
      done in method `generate` instead of `__init__`.

    This way, calling the ParserGenerator class becomes a way to
    check if the ParserGenerator accepts the grammar. (?)
    """

    callmakervisitor: GrammarVisitor

    # validator.validate_grammar[_v2] should not be called by ParserGenerator.
    # Instead, v1/v2 subclasses of ParserGenerator will call them
    # since only at that time they know if they are v1/v2.
    def __init__(self, grammar: Grammar, tokens: Set[str]):
        self.grammar = grammar
        self.tokens = tokens
        self.rules = grammar.rules
        validate_items(self.grammar.items, self.tokens)
        if "trailer" not in grammar.metas and "start" not in self.rules:
            raise ValidationError("Grammar without a trailer must have a 'start' rule")
        self.file: TextIO
        self.level = 0
        compute_nullables(self.rules) #XXX: Value is thrown away intentionally???
        self.first_graph, self.first_sccs = compute_left_recursives(self.rules)
        self.todo = self.rules.copy()  # Rules to generate
        self.counter = 0  # For name_rule()/name_loop()
        self.all_rules: Dict[str, Rule] = {}  # Rules + temporal rules
        self._local_variable_stack: List[List[str]] = []

    @contextlib.contextmanager
    def local_variable_context(self) -> Iterator[None]:
        self._local_variable_stack.append([])
        yield
        self._local_variable_stack.pop()

    @property
    def local_variable_names(self) -> List[str]:
        return self._local_variable_stack[-1]

    @abstractmethod
    def generate(self, file: TextIO, filename: str) -> None:
        self.file = file

    @contextlib.contextmanager
    def indent(self) -> Iterator[None]:
        self.level += 1
        try:
            yield
        finally:
            self.level -= 1

    def print(self, *args: object) -> None:
        if not args:
            print(file=self.file)
        else:
            print("    " * self.level, end="", file=self.file)
            print(*args, file=self.file)

    def printblock(self, lines: str) -> None:
        for line in lines.splitlines():
            self.print(line)

    #XXX: What does this do?
    def collect_todo(self) -> None:
        # I've tested that it is not invoked by the tests.
        raise NotImplementedError("collect_todo looks like a TODO feature.")
        done: Set[str] = set()
        while True:
            alltodo = list(self.todo)
            self.all_rules.update(self.todo)
            todo = [i for i in alltodo if i not in done]
            if not todo:
                break
            for rulename in todo:
                self.todo[rulename].collect_todo(self)
            done = set(alltodo)

    def artificial_rule_from_rhs(self, rhs: Rhs) -> str:
        self.counter += 1
        name = f"_tmp_{self.counter}"  # TODO: Pick a nicer name.
        self.todo[name] = Rule(name, None, rhs)
        return name

    def artificial_rule_from_repeat(self, node: Plain, is_repeat1: bool) -> str:
        self.counter += 1
        if is_repeat1:
            prefix = "_loop1_"
        else:
            prefix = "_loop0_"
        name = f"{prefix}{self.counter}"  # TODO: It's ugly to signal via the name.
        self.todo[name] = Rule(name, None, Rhs([Alt([TopLevelItem(None, node)])]))
        return name

    def artificial_rule_from_gather(self, node: Gather) -> str:
        self.counter += 1
        name = f"_gather_{self.counter}"
        self.counter += 1
        extra_function_name = f"_loop0_{self.counter}"
        extra_function_alt = Alt(
            [TopLevelItem(None, node.separator), TopLevelItem("elem", node.node)],
            action="elem",
        )
        self.todo[extra_function_name] = Rule(
            extra_function_name,
            None,
            Rhs([extra_function_alt]),
        )
        alt = Alt(
            [TopLevelItem("elem", node.node), TopLevelItem("seq", NameLeaf(extra_function_name))],
        )
        self.todo[name] = Rule(
            name,
            None,
            Rhs([alt]),
        )
        return name

    def dedupe_and_add_var(self, name: str) -> str:
        origname = name
        counter = 0
        while name in self.local_variable_names:
            counter += 1
            name = f"{origname}_{counter}"
        self.local_variable_names.append(name)
        return name


class NullableVisitor(GrammarVisitor):
    def __init__(self, rules: Dict[str, Rule]) -> None:
        self.rules = rules
        self.visited: Set[Any] = set()

    def visit_Rule(self, rule: Rule) -> bool:
        if rule in self.visited:
            return False
        self.visited.add(rule)
        if self.visit(rule.rhs):
            rule.nullable = True
        return rule.nullable

    def visit_Rhs(self, rhs: Rhs) -> bool:
        for alt in rhs.alts:
            if self.visit(alt):
                return True
        return False

    def visit_Alt(self, alt: Alt) -> bool:
        for item in alt.items:
            if not self.visit(item):
                return False
        return True

    def visit_Forced(self, force: Forced) -> bool:
        return True

    def visit_LookAhead(self, lookahead: Lookahead) -> bool:
        return True

    def visit_Opt(self, opt: Opt) -> bool:
        return True

    def visit_Repeat0(self, repeat: Repeat0) -> bool:
        return True

    def visit_Repeat1(self, repeat: Repeat1) -> bool:
        return False

    def visit_Gather(self, gather: Gather) -> bool:
        return False

    def visit_Cut(self, cut: Cut) -> bool:
        return False

    def visit_Group(self, group: Group) -> bool:
        return self.visit(group.rhs)

    def visit_TopLevelItem(self, item: TopLevelItem) -> bool:
        if self.visit(item.item):
            item.nullable = True
        return item.nullable

    def visit_NameLeaf(self, node: NameLeaf) -> bool:
        if node.value in self.rules:
            return self.visit(self.rules[node.value])
        # Token or unknown; never empty.
        return False

    def visit_StringLeaf(self, node: StringLeaf) -> bool:
        # The string token '' is considered empty.
        return not node.value

    def visit_ExternDecl(self, node: ExternDecl) -> bool:
        # Considered possibly empty.
        # XXX: "non-nullable" mark for ExternDecl?
        return True


def compute_nullables(rules: Dict[str, Rule]) -> None:
    """Compute which rules in a grammar are nullable.

    Thanks to TatSu (tatsu/leftrec.py) for inspiration.
    """
    nullable_visitor = NullableVisitor(rules)
    for rule in rules.values():
        nullable_visitor.visit(rule)


def compute_left_recursives(
    rules: Dict[str, Rule]
) -> Tuple[Dict[str, AbstractSet[str]], List[AbstractSet[str]]]:
    graph = make_first_graph(rules)
    sccs = list(sccutils.strongly_connected_components(graph.keys(), graph))
    for scc in sccs:
        if len(scc) > 1:
            for name in scc:
                rules[name].left_recursive = True
            # Try to find a leader such that all cycles go through it.
            leaders = set(scc)
            for start in scc:
                for cycle in sccutils.find_cycles_in_scc(graph, scc, start):
                    # print("Cycle:", " -> ".join(cycle))
                    leaders -= scc - set(cycle)
                    if not leaders:
                        raise ValueError(
                            f"SCC {scc} has no leadership candidate (no element is included in all cycles)"
                        )
            # print("Leaders:", leaders)
            leader = min(leaders)  # Pick an arbitrary leader from the candidates.
            rules[leader].leader = True
        else:
            name = min(scc)  # The only element.
            if name in graph[name]:
                rules[name].left_recursive = True
                rules[name].leader = True
    return graph, sccs


def make_first_graph(rules: Dict[str, Rule]) -> Dict[str, AbstractSet[str]]:
    """Compute the graph of left-invocations.

    There's an edge from A to B if A may invoke B at its initial
    position.

    Note that this requires the nullable flags to have been computed.
    """
    graph = {}
    vertices: Set[str] = set()
    for rulename, rhs in rules.items():
        graph[rulename] = names = rhs.initial_names()
        vertices |= names
    for vertex in vertices:
        graph.setdefault(vertex, set())
    return graph
