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
import traceback
from typing import Any
from stde.pegen.legacy.build import generate_code_from_file, CodeFromFileProducts
from stde.pegen.v2.build import (generate_code_from_file as generate_code_from_file_v2,
                                 CodeFromFileProducts as CodeFromFileProductsV2)
from stde.pegen.legacy.validator import validate_grammar
from stde.pegen.v2.validator import validate_grammar as validate_grammar_v2


def generate_python_code(
    args: argparse.Namespace,
) -> CodeFromFileProducts:
    try:
        return generate_code_from_file(
            args.grammar_file,
            args.output,
            sys.stdout if args.verbose_tokenization else None,
            sys.stdout if args.verbose_parsing else None,
            skip_actions=args.skip_actions,
        )
    except Exception as err:
        traceback.print_exception(err.__class__, err, None)
        raise  # Show traceback


def generate_python_code_v2(args: argparse.Namespace) -> CodeFromFileProductsV2:
    try:
        return generate_code_from_file_v2(
            args.grammar_file,
            args.output,
            sys.stdout if args.verbose_tokenization else None,
            sys.stdout if args.verbose_parsing else None,
            skip_actions=args.skip_actions,
        )
    except Exception as err:
        traceback.print_exception(err.__class__, err, None)
        raise  # Show traceback


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

    products: Any
    if args.mode == "v2":
        t0 = time.time()
        products = generate_python_code_v2(args)
        t1 = time.time()
        validate_grammar(products.grammar)
    elif args.mode == "legacy":
        t0 = time.time()
        products = generate_python_code(args)
        t1 = time.time()
        validate_grammar_v2(products.grammar)
    else:
        assert False, args.mode

    if args.verbose > 1:
        print("Raw Grammar:")
        for line in repr(products.grammar).splitlines():
            print(" ", line)

    if args.verbose:
        print("Clean Grammar:")
        for line in str(products.grammar).splitlines():
            print(" ", line)

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
