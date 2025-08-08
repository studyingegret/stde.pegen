#!/usr/bin/env python3.8

"""pegen -- PEG Generator.

Search the web for PEG Parsers for reference.
"""

import argparse
import sys
import time
import token
import traceback
from typing import Any, Union

#TODO: Clean types
from pegen.build import generate_code_from_file, CodeFromFileProducts
from pegen.build_v2 import (generate_code_from_file as generate_code_from_file_v2,
                            CodeFromFileProducts as CodeFromFileProductsV2)
from pegen.validator import validate_grammar


def generate_python_code(
    args: argparse.Namespace,
) -> CodeFromFileProducts:
    verbose: int = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4
    try:
        return generate_code_from_file(
            args.grammar_file,
            args.output,
            sys.stdout if verbose_tokenizer else None,
            sys.stdout if verbose_parser else None,
            skip_actions=args.skip_actions,
        )
    except Exception as err:
        if args.verbose:
            raise  # Show traceback
        traceback.print_exception(err.__class__, err, None)
        sys.stderr.write("For full traceback, use -v\n")
        sys.exit(1)


def generate_python_code_v2(args: argparse.Namespace) -> CodeFromFileProductsV2:
    verbose: int = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4
    try:
        return generate_code_from_file_v2(
            args.grammar_file,
            args.output,
            sys.stdout if verbose_tokenizer else None,
            sys.stdout if verbose_parser else None,
            skip_actions=args.skip_actions,
        )
    except Exception as err:
        if args.verbose:
            raise  # Show traceback
        traceback.print_exception(err.__class__, err, None)
        sys.stderr.write("For full traceback, use -v\n")
        sys.exit(1)


argparser = argparse.ArgumentParser(
    prog="pegen",
    description="Experimental PEG-like parser generator")
argparser.add_argument("-q", "--quiet", action="store_true", help="Don't print the parsed grammar")
argparser.add_argument("-v2", "--v2", action="store_true", help="Use v2 mode")
argparser.add_argument("-v", "--verbose", action="count", default=0,
                       help="Print timing stats; repeat for more debug output")
argparser.add_argument("grammar_file", type=argparse.FileType("r"), help="Grammar description")
argparser.add_argument("-o", "--output", metavar="OUT", default="parse.py",
                       help="Where to write the generated parser")
argparser.add_argument("--skip-actions", action="store_true",
                       help="Suppress code emission for rule actions")


def main() -> None:
    args = argparser.parse_args()

    products: Any
    if args.v2:
        t0 = time.time()
        products = generate_python_code_v2(args)
        t1 = time.time()
    else:
        t0 = time.time()
        products = generate_python_code(args)
        t1 = time.time()

    validate_grammar(products.grammar)

    if not args.quiet:
        if args.verbose:
            print("Raw Grammar:")
            for line in repr(products.grammar).splitlines():
                print(" ", line)

        print("Clean Grammar:")
        for line in str(products.grammar).splitlines():
            print(" ", line)

    if args.verbose:
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

    if args.verbose:
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
