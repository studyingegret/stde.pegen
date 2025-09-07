#!/usr/bin/env python3.8
#TODO: Port to have v2 version

""" Convert a grammar into a dot-file suitable for use with GraphViz

    For example:
        Generate the GraphViz file:
        # scripts/grammar_grapher.py data/python.gram > python.gv

        Then generate the graph...

        # twopi python.gv -Tpng > python_twopi.png

        or

        # dot python.gv -Tpng > python_dot.png

        NOTE: The _dot_ and _twopi_ tools seem to produce the most useful results.
              The _circo_ tool is the worst of the bunch. Don't even bother.
"""

import argparse
import sys
from typing import Any, List

sys.path.insert(0, ".")

from stde.pegen.legacy.build import load_grammar_from_file
from stde.pegen.legacy.grammar import (
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
)

argparser = argparse.ArgumentParser(
    prog="graph_grammar",
    description="Graph a grammar tree",
)
argparser.add_argument("grammar_file", help="The grammar file to graph")


def references_for_item(item: Any) -> List[Any]:
    if isinstance(item, Alt):
        return [_ref for _item in item.items for _ref in references_for_item(_item)]
    elif isinstance(item, Cut):
        return []
    elif isinstance(item, Forced):
        return references_for_item(item.node)
    elif isinstance(item, Group):
        return references_for_item(item.rhs)
    elif isinstance(item, Lookahead):
        return references_for_item(item.node)
    elif isinstance(item, TopLevelItem):
        return references_for_item(item.item)

    # NOTE NameLeaf must be before Leaf
    elif isinstance(item, NameLeaf):
        if item.value == "ENDMARKER":
            return []
        return [item.value]
    elif isinstance(item, Leaf):
        return []

    elif isinstance(item, Opt):
        return references_for_item(item.node)
    elif isinstance(item, Repeat):
        return references_for_item(item.node)
    elif isinstance(item, Rhs):
        return [_ref for alt in item.alts for _ref in references_for_item(alt)]
    elif isinstance(item, Rule):
        return references_for_item(item.rhs)
    elif isinstance(item, ExternDecl):
        return [item.name]
    else:
        raise RuntimeError(f"Unknown item: {type(item)}")


def main() -> None:
    args = argparser.parse_args()

    try:
        grammar = load_grammar_from_file(args.grammar_file).grammar
    except Exception as err:
        print("ERROR: Failed to parse grammar file", file=sys.stderr)
        sys.exit(1)

    references = {}
    for name, rule in grammar.rules.items():
        references[name] = set(references_for_item(rule))

    # Flatten the start node if has only a single reference
    root_node = "start"
    if start := references.get("start"):
        if len(start) == 1:
            root_node = list(start)[0]
            del references["start"]

    print("digraph g1 {")
    print('\toverlap="scale";')  # Force twopi to scale the graph to avoid overlaps
    print(f'\troot="{root_node}";')
    if start:
        print(f"\t{root_node} [color=green, shape=circle]")
    for name, refs in references.items():
        if refs:  # Ignore empty sets
            print(f"\t{name} -> {','.join(refs)};")
    print("}")


if __name__ == "__main__":
    main()
