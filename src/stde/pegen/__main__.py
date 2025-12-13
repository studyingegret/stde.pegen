#!/usr/bin/env python3.8

"""stde.pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

"""

"""

import argparse
import sys
import time
import token
#import traceback
from typing import Any
from stde.pegen.legacy import build as lg
from stde.pegen.v2 import build as v2
#from stde.pegen.legacy.validator import validate_grammar
#from stde.pegen.v2.validate import check_unreachable_rules as validate_grammar_v2


p = argparse.ArgumentParser(
    prog="stde.pegen",
    description="Experimental PEG-like parser generator")
p.set_defaults(mode="v2")
g = p.add_mutually_exclusive_group()
g.add_argument("--legacy", action="store_const", dest="mode", const="legacy",
               help="Use legacy mode")
g.add_argument("--v2", action="store_const", dest="mode", const="v2",
               help="Use v2 mode (default)")
p.add_argument("-v", "--verbose", action="count", default=0,
               help="Show more information. When provided once, show cleaned grammar."
                    "When provided twice, shwo timing stats and more.")
p.add_argument("--verbose-tokenization", action="store_true",
               help="Show debug output of tokenization of grammar source")
p.add_argument("--verbose-parsing", action="store_true",
               help="Show debug output of parsing of grammar source")
p.add_argument("grammar_file", type=argparse.FileType("r"),
               help="Grammar description")
p.add_argument("-o", "--output", metavar="OUT", default="parse.py",
               help="Where to write the generated parser")
p.add_argument("--skip-actions", action="store_true",
               help="Suppress code emission for rule actions")


def main() -> None:
    args = p.parse_args()

    t0 = time.time()

    md = v2 if args.mode == "v2" else lg
    products: Any # [emoji] asffdaffa!!!
    tokenizer_verbose_stream = sys.stdout if args.verbose_tokenization else None
    parser_verbose_stream = sys.stdout if args.verbose_parsing else None

    if args.verbose > 0:
        print("Parsing grammar")

    products = md.load_grammar_from_file(
        args.grammar_file,
        tokenizer_verbose_stream=tokenizer_verbose_stream,
        parser_verbose_stream=parser_verbose_stream)

    if args.verbose > 1:
        print("Raw Grammar:")
        for line in repr(products.grammar).splitlines():
            print(" ", line)

    if args.verbose > 0:
        print("Clean Grammar:")
        for line in str(products.grammar).splitlines():
            print(" ", line)
        print("Generating parser code")

    products = md.generate_code_from_grammar(
        products.grammar,
        output_file=args.output,
        skip_actions=args.skip_actions)

    if args.verbose > 1:
        print("First Graph:")
        for src, dsts in products.parser_code_generator.first_graph.items():
            print(f"  {src} -> {', '.join(dsts)}")
        print("First SCCS:")
        for scc in products.parser_code_generator.first_sccs:
            print(" ", scc, end="")
            if len(scc) > 1:
                print(
                    "  # Indirectly left-recursive; leaders:",
                    {name for name in scc if products.grammar.rules[name].leader},
                )
            else:
                name = next(iter(scc))
                if name in products.parser_code_generator.first_graph[name]:
                    print("  # Left-recursive")
                else:
                    print()

        t1 = time.time()

        dt = t1 - t0
        diag = products.grammar_tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print(f"Total time: {dt:.3f} sec; {nlines} lines", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(products.grammar_tokenizer._tokens):10}")
        print(f"        cache : {len(products.grammar_parser._cache):10}")


if __name__ == "__main__":
    main()
