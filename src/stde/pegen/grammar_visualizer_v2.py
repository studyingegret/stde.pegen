import argparse
import sys
from typing import Any, Callable, Iterator, List, Tuple

from stde.pegen.build_v2 import load_grammar_from_file
from stde.pegen.grammar_v2 import Grammar, Rule

argparser = argparse.ArgumentParser(
    prog="stde.pegen", description="Pretty print the AST for a given PEG grammar" #TODO
)
argparser.add_argument("filename", help="Grammar description")


# Note: self is not heavily used so it is possible to write this
# with functions, without using a class without too much trouble.
class ASTGrammarPrinter:
    def print_grammar_ast(self, grammar: Grammar, printer: Callable[..., None] = print) -> None:
        for rule in grammar.rules.values():
            printer(self.print_nodes_recursively(rule))

    def children(self, node: Any) -> Iterator[Any]:
        for value in node:
            if isinstance(value, list):
                yield from value
            else:
                yield value

    def children_and_name(self, node: Any) -> Tuple[List[Any], str]:
        children = list(self.children(node))
        if not children:
            return children, repr(node)
        return children, node.__class__.__name__

    def print_nodes_recursively(self, node: Any, prefix: str = "", istail: bool = True) -> str:
        children, name = self.children_and_name(node)
        line = prefix + ("└──" if istail else "├──") + name + "\n"
        if not children:
            return line
        suffix = "   " if istail else "│  "

        *children, last = children
        for child in children:
            line += self.print_nodes_recursively(child, prefix + suffix, False)
        line += self.print_nodes_recursively(last, prefix + suffix, True)

        return line


def main() -> None:
    args = argparser.parse_args()

    try:
        grammar = load_grammar_from_file(args.filename).grammar
    except Exception:
        print("ERROR: Failed to parse grammar file", file=sys.stderr)
        sys.exit(1)

    visitor = ASTGrammarPrinter()
    visitor.print_grammar_ast(grammar)


if __name__ == "__main__":
    main()
