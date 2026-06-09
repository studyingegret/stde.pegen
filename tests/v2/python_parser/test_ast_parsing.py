"""Test pure Python parser against cpython parser."""

import ast
import difflib
from functools import partial
import io
import sys
import textwrap
import tokenize
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest


def require_py_version(item: Any, version: Tuple[int, ...], *, reason: str) -> Any:
    """Helper to skip test items based on Python version."""
    reason = reason.format("Python " + ".".join(map(str, version)) + "+")
    return pytest.param(item, marks=pytest.mark.skipif(sys.version_info < version, reason=reason))


@pytest.mark.parametrize("filename", [
    require_py_version(
        "advanced_decorators.py", (3, 9), reason="Valid only in {}"),
    "assignment.py",
    "async.py",
    "call.py",
    "comprehensions.py",
    "expressions.py",
    "fstrings.py",
    "function_def.py",
    "imports.py",
    "lambdas.py",
    require_py_version(
        "multi_statement_per_line.py", (3, 9), reason="Col offset match only on {}"),
    "no_newline_at_end_of_file.py",
    "no_newline_at_end_of_file_with_comment.py",
    require_py_version(
        "pattern_matching.py", (3, 10), reason="Valid only in {}"), # Note: 20KB, expect to take longer
    "simple_decorators.py",
    "statements.py",
    require_py_version(
        "try_except_group.py", (3, 11), reason="except* allowed only in {}"),
    require_py_version(
        "type_params.py", (3, 12), reason="type declarations allowed only in {}"),
    require_py_version(
        "with_statement_multi_items.py", (3, 9), reason="Parenthesized with items allowed only in {}"),
])
def test_parser(python_parse_file, python_parse_str, filename, pytestconfig):
    path = Path(__file__).parent / "data" / filename
    with open(path) as f:
        source = f.read()

    kwargs = {"include_attributes": True}
    if sys.version_info >= (3, 9):
        kwargs["indent"] = "  " #pyright:ignore
    dump_ast = partial(ast.dump, **kwargs)

    for part in source.split("\n\n\n"):
        original = ast.parse(part)

        try:
            pp_ast = python_parse_str(
                part, "exec",
                verbose_tokenizer_stream=sys.stdout if pytestconfig.option.v2_python_parser_verbose_tokenizer else None,
                verbose_parser_stream=sys.stdout if pytestconfig.option.v2_python_parser_verbose_parser else None
            )
        except Exception:
            temp = io.StringIO(part)
            print("Parsing failed:")
            print("Source is:")
            print(textwrap.indent(part, "  "))
            #temp = io.StringIO(part) #XXX:?
            print("Token stream is:")
            for t in tokenize.generate_tokens(temp.readline):
                print(t)
            print()
            print("CPython ast is:")
            print(dump_ast(original))
            raise

        o = dump_ast(original)
        p = dump_ast(pp_ast)
        diff = "\n".join(
            difflib.unified_diff(o.split("\n"), p.split("\n"), "cpython", "python-pegen",
                                 n=pytestconfig.option.v2_python_parser_diff_ncontext)
        )
        if diff:
            print(part)
            print(diff)
        assert not diff

    o = dump_ast(ast.parse(source))
    p = dump_ast(python_parse_file(path))
    diff = "\n".join(difflib.unified_diff(o.split("\n"), p.split("\n"), "cpython", "python-pegen",
                                          n=pytestconfig.option.v2_python_parser_diff_ncontext))
    assert not diff
