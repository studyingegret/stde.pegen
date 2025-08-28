"""Use utilities in module build or build_v2 instead when possible."""
# XXX: Overlap with build module?

import importlib.util
import io
import sys
import textwrap
import tokenize
from typing import IO, Any, Dict, Final, Optional, Type, Union, cast
from contextlib import contextmanager

from stde.pegen.parser_v2 import BaseParser

from stde.pegen.grammar_v2 import Grammar
from stde.pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from stde.pegen.parser_v2 import BaseParser
from stde.pegen.python_generator_v2 import PythonParserGenerator
from stde.pegen.tokenizer import Tokenizer


def import_file(full_name: str, path: str) -> Any:
    """Import a python module from a path"""

    spec = importlib.util.spec_from_file_location(full_name, path)
    assert spec
    mod = importlib.util.module_from_spec(spec)

    # We assume this is not None and has an exec_module() method.
    # See https://docs.python.org/3/reference/import.html?highlight=exec_module#loading
    loader = cast(Any, spec.loader)
    loader.exec_module(mod)
    return mod


# Note: build.generate_parser_from_grammar can replace this
def generate_parser(
    grammar: Grammar, parser_path: Optional[str] = None, parser_name: str = "GeneratedParser",
    *, # For maximum compatibility
    source_name: str = "<string>"
) -> Type[BaseParser]:
    # Generate a parser.
    out = io.StringIO()
    genr = PythonParserGenerator(grammar)
    genr.generate(out, source_name)

    # Load the generated parser class.
    ns: Dict[str, Any] = {}
    if parser_path:
        with open(parser_path, "w") as f:
            f.write(out.getvalue())
        mod = import_file("py_parser", parser_path)
        return getattr(mod, parser_name)
    else:
        exec(out.getvalue(), ns)
        return ns[parser_name]


def parse_string(
    source: str, parser_class: Type[BaseParser], *, dedent: bool = True, verbose: bool = False
) -> Any:
    # Run the parser on a string.
    if dedent:
        source = textwrap.dedent(source)
    parser = parser_class.from_text(source, verbose_stream=sys.stdout if verbose else None)
    result = parser.start()
    if result is None:
        raise parser.make_syntax_error("invalid syntax")
    return result


def parse_string2(parser_class: Type[BaseParser], string: str,
                  verbose_tokenizer: bool = False, verbose_parser: bool = False) -> Any:
    with io.StringIO(string) as f:
        tokengen = tokenize.generate_tokens(f.readline)
        tokenizer = Tokenizer(tokengen, verbose_stream=sys.stdout if verbose_tokenizer else None)
        parser = parser_class(tokenizer, verbose_stream=sys.stdout if verbose_parser else None)
        return parser.start()


def generate_parser_from_string(
    source: str,
    *, # For maximum compatibility
    source_name: str = "<string>"
) -> Type[BaseParser]:
    """Combines parse_string and generate_parser."""
    return generate_parser(parse_string(source, GrammarParser), source_name=source_name)


def print_memstats() -> bool:
    MiB: Final = 2**20
    try:
        import psutil
    except ImportError:
        return False
    print("Memory stats:")
    process = psutil.Process()
    meminfo = process.memory_info()
    res = {}
    res["rss"] = meminfo.rss / MiB
    res["vms"] = meminfo.vms / MiB
    if sys.platform == "win32":
        res["maxrss"] = meminfo.peak_wset / MiB
    else:
        # See https://stackoverflow.com/questions/938733/total-memory-used-by-python-process
        import resource  # Since it doesn't exist on Windows.

        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            factor = 1
        else:
            factor = 1024  # Linux
        res["maxrss"] = rusage.ru_maxrss * factor / MiB
    for key, value in res.items():
        print(f"  {key:12.12s}: {value:10.0f} MiB")
    return True
