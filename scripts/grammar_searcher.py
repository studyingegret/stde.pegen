#!/usr/bin/env python3.8
#TODO
#TODO: Port to have v2 version

"""[TODO] Search tokens in a rule.

See which rules may reach the token "==" within 3 recursions:

    python scripts/grammar_searcher.py data/python.gram "'==':<=3" | dot -Tsvg > python.svg

See which rules may use the rule "primary" directly:

    python scripts/grammar_searcher.py data/python.gram "primary:<=1" | dot -Tsvg > python.svg

Query format:
    query = item ":" strict? op limit
    item = <Python string> # Matches a string (single or double quoted)
         | <Python name> # Matches a rule or extern declaration (in v2)
    op = "<" | "==" | ">" | "<=" | ">="
                      # Rule must possibly reach [item] in
                      # ([op]: less than/equal to/more than etc.) [limit] recursions
    strict = "strict" # When present, rule must only possibly reach [item]
                      # in (less than/equal to/more than etc.) [limit] recursions.
                      # e.g. With "a: b | c; c: b",
                      # a is accepted by "b:>1"
                      # but rejected by query "b:strict>1"
    limit = [0-9]+
          | "*" # = infinity

Note: strict flag is not supported yet.

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

---

Example:

    python scripts/grammar_searcher.py data/expr.gram "term:==1" "atom:<=3" "'+':<=2"

Expected output:

    expr
    factor,term,expr
    expr,start,factor

"""

import argparse
from enum import Enum, IntEnum
import sys
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, List, NamedTuple, Set, Dict, Tuple, Union, cast
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager
import operator
from ast import literal_eval

from pegen import build, build_v2, grammar as grammar_mod, grammar_v2

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
    PositiveLookahead,
    NegativeLookahead,
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

parser_class = build_v2.generate_parser_from_grammar("""
@base CharBasedParser
@header '''
from ast import literal_eval
def process_string(s):
    return literal_eval(s)
'''
start: item ":" strict? op limit $
item: string { (True, string) } | name { (False, name) }
name: a=letter+ { "".join(a) }
letter: "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h"
      | "i" | "j" | "k" | "l" | "m" | "n" | "o" | "p"
      | "q" | "r" | "s" | "t" | "u" | "v" | "w" | "x"
      | "y" | "z" | "A" | "B" | "C" | "D" | "E" | "F"
      | "G" | "H" | "I" | "J" | "K" | "L" | "M" | "N"
      | "O" | "P" | "Q" | "R" | "S" | "T" | "U" | "V"
      | "W" | "X" | "Y" | "Z"
string: '"' a=(!'"' any_char)* '"' { process_string('"' + "".join(a) + '"') }
      | "'" a=(!"'" any_char)* "'" { process_string("'" + "".join(a) + "'") }
op: "<=" | ">=" | "<" | "==" | ">"
strict: "strict"
limit: integer | "*"
integer: a=number+ { int("".join(a)) }
number: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
extern any_char
""").parser_class

class ItemType(IntEnum):
    NAME = 0
    STRING = 1

    def __repr__(self) -> str:
        #return f"{self.__class__.__name__}.{self._name_}"
        return self._name_

class Compare(Enum):
    # cast is necessary or Pylance treats as functions(methods?)
    LT = cast(Callable[..., bool], operator.lt)
    EQ = cast(Callable[..., bool], operator.eq)
    GT = cast(Callable[..., bool], operator.gt)
    LE = cast(Callable[..., bool], operator.le)
    GE = cast(Callable[..., bool], operator.ge)

compare_table = {
    "<": Compare.LT,
    "==": Compare.EQ,
    ">": Compare.GT,
    "<=": Compare.LE,
    ">=": Compare.GE,
}

class Item(NamedTuple):
    type: ItemType
    string: str

    def __repr__(self) -> str:
        if self.type == ItemType.NAME:
            return f"Name({self.string!r})"
        else:
            return f"String({self.string!r})"

class Query(NamedTuple):
    item: Item
    strict: bool
    op: Compare
    limit: int

def _parse_query(s: str) -> Query:
    parser = parser_class.from_text(s)
    res = parser.start()
    if res is None:
        raise parser.make_syntax_error(f"Cannot parse query {s}.")
    #print(res)
    item = Item(ItemType.STRING if res[0][0] else ItemType.NAME, res[0][1])
    return Query(item, bool(res[2]), compare_table[res[3]], res[4]) #type:ignore


class Visitor(GrammarVisitor):
    def __init__(self, grammar: "build.Grammar | build_v2.Grammar",
                 positive_lookahead_as_usage: bool = False,
                 negative_lookahead_as_usage: bool = False,):
        self.grammar = grammar
        self.positive_lookahead_as_usage = positive_lookahead_as_usage
        self.negative_lookahead_as_usage = negative_lookahead_as_usage
        self.graph: Dict[Item, List[str]] = {}
        self.dedupe_graph: Dict[Item, Set[str]] = {}
        self.current_rule_name: str = ""

    def compute_graph(self) -> None:
        self.visit(self.grammar.rules.values())

    @contextmanager
    def in_rule(self, name: str) -> Iterator[None]:
        self.current_rule_name = name
        yield
        self.current_rule_name = ""

    def add_item(self, item: Item) -> None:
        if item not in self.dedupe_graph:
            self.dedupe_graph[item] = set()
            self.graph[item] = []
        if self.current_rule_name not in self.dedupe_graph[item]:
            self.dedupe_graph[item].add(self.current_rule_name)
            self.graph[item].append(self.current_rule_name)

    def visit_PositiveLookahead(self, lkh: PositiveLookahead) -> None:
        if not self.positive_lookahead_as_usage:
            return
        self.visit(lkh.node)

    def visit_NegativeLookahead(self, lkh: NegativeLookahead) -> None:
        if not self.negative_lookahead_as_usage:
            return
        self.visit(lkh.node)

    def visit_Rule(self, rule: Rule) -> None:
        with self.in_rule(rule.name):
            self.visit(rule.rhs)

    def visit_NameLeaf(self, leaf: Union[grammar_mod.NameLeaf, grammar_v2.NameLeaf]) -> None:
        self.add_item(Item(ItemType.NAME, leaf.value))

    def visit_StringLeaf(self, leaf: Union[grammar_mod.StringLeaf, grammar_v2.StringLeaf]) -> None:
        self.add_item(Item(ItemType.STRING, literal_eval(leaf.value)))


def make_used_by_graph(grammar: "build.Grammar | build_v2.Grammar", args: argparse.Namespace
                       ) -> Dict[Item, List[str]]:
    visitor = Visitor(grammar, args.positive_lookahead_as_usage, args.negative_lookahead_as_usage)
    visitor.compute_graph()
    return visitor.graph


class Node(NamedTuple):
    item: Item
    distance: int


def process_query(query: Query, graph: Dict[Item, List[str]]) -> List[str]:
    if query.strict:
        raise NotImplementedError("strict feature in progress")
    max_distance = (query.limit - 1 if query.op == Compare.LT
                    else query.limit if query.op == Compare.EQ
                    else float("inf"))
    q: deque[Node] = deque([Node(query.item, 0)])
    visited: Set[str] = set()
    res: List[str] = []
    while q:
        x, distance = q.popleft()
        if x.type == ItemType.NAME and x.string in visited: continue
        visited.add(x.string)

        if x in graph:
            for y in graph[x]:
                if y not in visited:
                    new_distance = distance + 1
                    if new_distance > max_distance:
                        continue # Prune
                    # Note: Always a name since strings cannot use other rules
                    q.append(Node(Item(ItemType.NAME, y), new_distance))
                    if query.op._value_(new_distance, query.limit):
                        res.append(y)

    return res


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

    graph = make_used_by_graph(grammar, args)
    #print(graph)

    for query in args.queries:
        res = process_query(query, graph)
        print(",".join(res) or "(none)")


if __name__ == "__main__":
    #raise NotImplementedError("Script is TODO")
    p = argparse.ArgumentParser(
        prog="graph_grammar",
        description=__doc__, #type:ignore
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("grammar_file", type=argparse.FileType("r"),
                   help="The grammar file ('-' for stdin).")
    p.add_argument("queries", nargs="*", type=_parse_query,
                   help="Queries.")
    p.add_argument("-v2", action="store_true",
                   help="Parse grammar as v2.")
    p.add_argument("--positive-lookahead-as-usage", "--lkh-as-usage", action="store_false",
                   help="Treat positive lookahead (&x) as usage.")
    p.add_argument("--negative-lookahead-as-usage", "--neglkh-as-usage", action="store_true",
                   help="Treat negative lookahead (!x) as usage.")
    main(p.parse_args())
