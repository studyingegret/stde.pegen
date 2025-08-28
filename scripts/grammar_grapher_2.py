#!/usr/bin/env python3.8
#TODO: Port to have v2 version

"""Convert a grammar into a dot-file suitable for use with GraphViz

Recommended usage:

    python scripts/grammar_grapher_2.py data/python.gram | dot -Tsvg > python.svg

Open the result SVG file in an photo viewer that supports SVG.
If you don't have one, you can open it in your browser.
(If the browser shows a blank screen, try scrolling and zooming out to see the graph.)

It is also possible to generate PNG, though resolution will be worse
(worse than screenshotting SVG rendering):

    python scripts/grammar_grapher_2.py data/python.gram | dot -Tpng > python.png

Or just get the dot-file:

    python scripts/grammar_grapher_2.py data/python.gram

By default, rules starting with invalid_ are skipped.

---

Current limitation: Rules that aren't used by any other rule are not shown.
For example, try graphing data/isolated.gram.

This limitation applies after options (e.g. --ignore) are applied.
(e.g. If B is the only rule that uses A, and `--ignore B` is used, then A does not appear.)

Note: This limitation also exists in the old grammar grapher.

---

Try these examples:
python scripts/grammar_grapher_2.py data/python.gram -hl return_stmt | dot -Tsvg > python.svg
python scripts/grammar_grapher_2.py data/python.gram -hl return_stmt --no-terminals | dot -Tsvg > python.svg
python scripts/grammar_grapher_2.py data/python.gram -s return_stmt | dot -Tsvg > python.svg
python scripts/grammar_grapher_2.py data/python.gram -s return_stmt --no-terminals | dot -Tsvg > python.svg
python scripts/grammar_grapher_2.py data/python.gram -s return_stmt --reverse-alts --no-terminals | dot -Tsvg > python-reverse.svg
"""

import argparse
import sys
from typing import Any, Iterable, Iterator, List, Set, Dict, Tuple
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager

sys.path.insert(0, ".")

#from stde.pegen.build import load_grammar_from_file
#from stde.pegen.build_v2 import load_grammar_from_file
from stde.pegen.grammar import (
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

DEFAULT_STYLE = """\
    overlap="scale"  // Force twopi to scale the graph to avoid overlaps
    bgcolor="none"
    node [fontname="Consolas", shape=box, style="rounded,filled", color=none, fillcolor="#f0f0f0"]
    edge [color="#666", arrowhead=vee]
"""


#@dataclass
#class Item:
#    string: str
#    #type:


class Visitor(GrammarVisitor):
    def __init__(self, grammar: Grammar, terminals: Set[str],
                 include_invalid: bool = False,
                 reverse_alts: bool = False, reverse_alt: bool = False):
        self.grammar = grammar
        self.terminals = terminals
        self.include_invalid = include_invalid
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
        if not self.include_invalid and rule.name.startswith("invalid_"):
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
        if not self.include_invalid and nameleaf.value.startswith("invalid_"):
            return
        self.link_to(nameleaf.value)
        if nameleaf.value not in self.terminals:
            if nameleaf.value not in self.grammar.items:
                current_rule_name = (self._current_rule_name_stack[-1]
                                     if self._current_rule_name_stack
                                     else "(??)")
                print(f"Warning: Unknown name {nameleaf.value} (in rule {current_rule_name})",
                      file=sys.stderr)
            else:
                self.visit(self.grammar[nameleaf.value])

    def visit_ExternDecl(self, decl: ExternDecl) -> None:
        if not self.include_invalid and decl.name.startswith("invalid_"):
            return
        if decl.name not in self.unordered_graph:
            self.init_name(decl.name)
            self.dfn_order.append(decl.name)
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
        from stde.pegen.build_v2 import load_grammar_from_file
        terminals = TERMINALS_V1
    else:
        from stde.pegen.build import load_grammar_from_file #type:ignore
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

    visitor = Visitor(grammar, terminals, args.include_invalid, args.reverse_alts, args.reverse_alt) #type:ignore #... Migrating
    if args.subgraph:
        visitor.visit(grammar[args.subgraph])
    else:
        for rule in grammar.rules.values():
            visitor.visit(rule)

    root_node = (args.subgraph if args.subgraph
                 else "start" if "start" in grammar.items
                 else None)
    print("digraph g1 {")
    print(args.global_style)
    if root_node:
        print(f'    root="{root_node}";')
        print(f'    {root_node} [color=green, fontcolor="#427934", shape=circle, fillcolor=white]')

    items: Iterable[Tuple[str, Iterable[str]]] #Settle mypy
    if args.canonical == "dfn_order":
        items = ((name, visitor.graph[name]) for name in visitor.dfn_order)
    elif args.canonical == "name_sort":
        items = sorted(visitor.graph.items(), key=lambda x: x[0])
    else:
        items = visitor.graph.items()
    outlinked: Set[str] = set()
    mentioned: Set[str] = set()
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
        outlinked.add(name)
        mentioned.add(name)
        mentioned.update(s.split(","))
        print(f"    {name} -> {s};")

    # Note: printing nodes before edges affects rendered layout
    # Precedence: args.highlight > mentioned - outlinked

    final: Set[str] = set()
    penwidth = "2.5" if args.higher_contrast_highlight else "1.6"
    color = "#7b7800" if args.higher_contrast_highlight else "#b9b400"
    #fillcolor = "#fffedf"
    fillcolor = "#fffeea"
    for name in args.highlight:
        if name in mentioned:
            # Note: `color` is picked deeper and `fillcolor` lighter to make it more colorblind-friendly
            # (even when higher_contrast_highlight is off -- people can forget)
            if name == root_node:
                print(f'    {name} [color="{color}", fontcolor=black, fillcolor="{fillcolor}", penwidth="{penwidth}"]')
            else:
                print(f'    {name} [color="{color}", fillcolor="{fillcolor}", penwidth="{penwidth}"]')
            final.add(name)
        else:
            print(f"{name} is not highlighted because it is not present in the result graph",
                  file=sys.stderr)

    if not args.dont_fade_no_outgoing_rules:
        for name in mentioned - outlinked:
            if name not in final:
                print(f'    {name} [fontcolor="#777", fillcolor="#fafafa"]')
                #final.add(name)

    print("}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        prog="graph_grammar.py",
        description=__doc__, #type:ignore
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("grammar_file", type=argparse.FileType("r"),
                   help="The grammar file to graph ('-' for stdin).")
    p.add_argument("-s", "--subgraph", metavar="NAME",
                   help="Only display the subgraph of the grammar tree that NAME uses.")
    p.add_argument("-v2", action="store_true",
                   help="Parse grammar as v2.")
    p.add_argument("-t", "--terminals", metavar="NAMES", type=_parse_terminals, default=(True, set()),
                   help="Mark these names as terminals (they will not be followed). "
                        "[comma-separated list of names; also see below] "
                        "This replaces the list of default terminals, unless a '+' "
                        "is present before the list of names (e.g. '+one,two').")
    p.add_argument("-hl", "--highlight", metavar="NAMES", type=lambda x: set(x.split(",")), default=set(),
                   help="Highlight these names. [comma-separated list of names]")
    p.add_argument("--skip", "--ignore", metavar="NAMES", type=lambda x: set(x.split(",")), default={"ENDMARKER"},
                   help="Skip these names. [comma-separated list of names]")
    p.add_argument("--include-invalid", action="store_true",
                   help="Don't ignore rules that start with 'invalid_'.")
    p.add_argument("--canonical", choices=["name_sort", "dfn_order", "none"], default="dfn_order",
                   help="Canonicalize graph dict to avoid iteration order randomness. "
                        "Default dfn_order.")
    p.add_argument("--no-terminals", action="store_true",
                   help="Skip terminal nodes.") #...
    p.add_argument("--reverse-alts", action="store_true",
                   help="Reverse traverse order of top-level branches of each rule "
                        "(gives another view of the graph).")
    p.add_argument("--reverse-alt", action="store_true",
                   help="Reverse traverse order of items of each branch "
                        "(gives another view of the graph).")
    p.add_argument("--dont-fade-no-outgoing-rules", action="store_true",
                   help="Don't fade rules that don't use other rules.")
    p.add_argument("--higher-contrast-highlight", action="store_true",
                   help="Use more visible highlight style (darker and thicker outline).")
    p.add_argument("--global-style", action="store_true", default=DEFAULT_STYLE,
                   help="Replace the default style string in output dot, put before"
                        "all nodes and edges. "
                        f"Default style string is {DEFAULT_STYLE.replace("\n", "; ")!r}.")
    main(p.parse_args())
