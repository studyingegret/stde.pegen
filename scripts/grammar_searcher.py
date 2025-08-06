#!/usr/bin/env python3.8
#TODO
#TODO: Port to have v2 version

"""[TODO] Search tokens in a rule.

See which rules may reach the token "==" within 3 recursions:

    python scripts/grammar_searcher.py data/python.gram "'==':<=3" | dot -Tsvg > python.svg

See which rules may use the rule "primary" directly:

    python scripts/grammar_searcher.py data/python.gram "primary:<=1" | dot -Tsvg > python.svg

Query format:
    query = match ":" strict? op number
    match = <Python string> # Matches a string (single or double quoted)
          | <Python name> # Matches a rule or extern declaration
    op = "<" | "==" | ">" | "<=" | ">="
                      # Rule must possibly reach [match] in
                      # (less than/equal to/more than etc.) [number] recursions
    strict = "strict" # When present, rule must only possibly reach [match]
                      # in (less than/equal to/more than etc.) [number] recursions.
                      # e.g. With "a: b | c; c: b",
                      # a is accepted by "b:>1"
                      # but rejected by query "b:strict>1"

Multiple queries are possible: just pass them as a list of arguments.

Output format: [TODO]

Open the result SVG file in an photo viewer that supports SVG.
If you don't have one, you can open it in your browser.
(If the browser shows a blank screen, try scrolling and zooming out to see the graph.)

It is also possible to generate PNG, though resolution will be worse
(worse than screenshotting SVG rendering):

    python scripts/grammar_searcher.py data/python.gram "NAME:<=3" | dot -Tpng > python.png

Or just get the dot-file:

    python scripts/grammar_searcher.py data/python.gram "NAME:<=3"
"""

import argparse
import sys
from typing import Any, Iterable, Iterator, List, Set, Dict, Tuple
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager

sys.path.insert(0, ".")

#from pegen.build import load_grammar_from_file
#from pegen.build_v2 import load_grammar_from_file
from pegen.grammar import (
    Alt,
    Cut,
    Forced,
    Grammar,
    Group,
    Leaf,
    Lookahead,
    TopLevelItem,
    NameLeaf,
    Opt,
    Repeat,
    Rhs,
    Rule,
    ExternDecl,
    GrammarVisitor,
)

#...
TERMINALS_V1 = {"SOFT_KEYWORD", "NAME", "NUMBER", "STRING",
                "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", "OP", "TYPE_COMMENT",
                "NEWLINE", "DEDENT", "INDENT", "ENDMARKER", "ASYNC", "AWAIT"}


#@dataclass
#class Item:
#    string: str
#    #type:


class Visitor(GrammarVisitor):
    def __init__(self, grammar: Grammar, terminals: Set[str],
                 reverse_alts: bool = False, reverse_alt: bool = False):
        self.grammar = grammar
        self.terminals = terminals
        self.reverse_alts = reverse_alts
        self.reverse_alt = reverse_alt
        self.unordered_graph: Dict[str, Set[str]] = {}
        self.graph: Dict[str, List[str]] = {}
        self._current_rule_name_stack: deque[str] = deque()
        self.dfn_order: List[str] = []

    @contextmanager
    def in_rule(self, name: str) -> Iterator[None]:
        self._current_rule_name_stack.append(name)
        yield
        self._current_rule_name_stack.pop()

    def init_name(self, name: str) -> None:
        self.unordered_graph[name] = set()
        self.graph[name] = []

    def link_to(self, name: str) -> None:
        if self._current_rule_name_stack:
            current_rule_name = self._current_rule_name_stack[-1]
            if name not in self.unordered_graph[current_rule_name]:
                self.unordered_graph[current_rule_name].add(name)
                self.graph[current_rule_name].append(name)

    def visit_Rule(self, rule: Rule) -> None:
        if rule.name in self.unordered_graph:
            return
        self.init_name(rule.name)
        self.dfn_order.append(rule.name)
        if rule.name not in self.terminals:
            with self.in_rule(rule.name):
                self.visit(rule.rhs)

    def visit_Rhs(self, rhs: Rhs) -> None:
        self.visit(reversed(rhs.alts) if self.reverse_alts else rhs.alts)

    def visit_Alt(self, alt: Alt) -> None:
        self.visit(reversed(alt.items) if self.reverse_alt else alt.items)

    def visit_NameLeaf(self, nameleaf: NameLeaf) -> None:
        self.link_to(nameleaf.value)
        if nameleaf.value not in self.terminals:
            if nameleaf.value not in self.grammar.items:
                print(f"Warning: Unknown name {nameleaf.value}")
            else:
                self.visit(self.grammar[nameleaf.value])

    #TODO: Untested
    def visit_ExternDecl(self, decl: ExternDecl) -> None:
        if decl.name not in self.unordered_graph:
            self.dfn_order.append(decl.name)
            self.init_name(decl.name)
        # ExternDecl may also be visited as the root item
        # but link_to handles this this case
        self.link_to(decl.name)


def _parse_terminals(s: str) -> Tuple[bool, Set[str]]:
    if s.startswith("+"):
        s = s[1:]
        extend = True
    else:
        extend = False
    return (extend, set(s.split(",")))


def main(args: argparse.Namespace) -> None:
    if args.v2:
        from pegen.build_v2 import load_grammar_from_file
        terminals = TERMINALS_V1
    else:
        from pegen.build import load_grammar_from_file #type:ignore
        terminals = TERMINALS_V1 #TODO: Depend on base class
    try:
        grammar = load_grammar_from_file(args.grammar_file).grammar
    except Exception as err:
        print("ERROR: Failed to parse grammar file", file=sys.stderr)
        sys.exit(1)

    if args.terminals[0]:
        terminals |= args.terminals[1]
    else:
        terminals = args.terminals[1]

    visitor = Visitor(grammar, terminals, args.reverse_alts, args.reverse_alt) #type:ignore #... Migrating
    if args.subgraph:
        visitor.visit(grammar[args.subgraph])
    else:
        for rule in grammar.rules.values():
            visitor.visit(rule)

    root_node = (args.subgraph if args.subgraph
                 else "start" if "start" in grammar.items
                 else None)
    print("digraph g1 {")
    print('\toverlap="scale";')  # Force twopi to scale the graph to avoid overlaps
    print('\tnode [fontname="Consolas", shape=box, style="rounded,filled", color=none, fillcolor="#f0f0f0"]')
    print('\tedge [color="#666", arrowhead=vee]')
    if root_node:
        print(f'\troot="{root_node}";')
        print(f'\t{root_node} [color=green, fontcolor="#427934", shape=circle, fillcolor=white]')

    for name in args.highlight:
        # Note: `color` is picked deeper and `fillcolor` lighter to make it more colorblind-friendly
        print(f'\t{name} [color="#b9b400", fillcolor="#fffedf", penwidth="1.5"]')

    items: Iterable[Tuple[str, Iterable[str]]] #Settle mypy
    if args.canonical == "dfn_order":
        items = ((name, visitor.graph[name]) for name in visitor.dfn_order)
    elif args.canonical == "name_sort":
        items = sorted(visitor.graph.items(), key=lambda x: x[0])
    else:
        items = visitor.graph.items()
    for name, edges in items:
        if name in args.skip:
            continue
        edges = (name for name in edges if name not in args.skip)
        if not args.include_invalid:
            if name.startswith("invalid_"):
                continue
            edges = (name for name in edges if not name.startswith("invalid_"))
        if args.no_terminals:
            if name in terminals:
                continue
            edges = (name for name in edges if name not in terminals)
        if args.canonical == "name_sort":
            edges = sorted(edges)
        s = ','.join(edges)
        if not s:
            continue # "name -> ;" is syntax error; s is empty means all edges are filtered out
        print(f"\t{name} -> {s};")
    print("}")


if __name__ == "__main__":
    raise NotImplementedError("Script is TODO")
    p = argparse.ArgumentParser(
        prog="graph_grammar",
        description=__doc__, #type:ignore
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("grammar_file", type=argparse.FileType("r"),
                   help="The grammar file to graph ('-' for stdin).")
    main(p.parse_args())
