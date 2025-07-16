""""Conftest for pure python parser."""

from pathlib import Path

import pytest
from pegen.build import load_grammar_from_file
from pegen.utils import generate_parser


@pytest.fixture(scope="session")
def python_parser_cls():
    grammar_path = Path(__file__).parent.parent.parent / "data/python.gram"
    grammar = load_grammar_from_file(grammar_path).grammar
    source_path = str(Path(__file__).parent / "parser_cache" / "py_parser.py")
    parser_cls = generate_parser(grammar, source_path, "PythonParser", source_name=str(grammar_path))

    return parser_cls


@pytest.fixture(scope="session")
def python_parse_file():
    grammar_path = Path(__file__).parent.parent.parent / "data/python.gram"
    grammar = load_grammar_from_file(grammar_path).grammar
    source_path = str(Path(__file__).parent / "parser_cache" / "py_parser.py")
    parser_cls = generate_parser(grammar, source_path, "parse_file", source_name=str(grammar_path))

    return parser_cls


@pytest.fixture(scope="session")
def python_parse_str():
    grammar_path = Path(__file__).parent.parent.parent / "data/python.gram"
    grammar = load_grammar_from_file(grammar_path).grammar
    source_path = str(Path(__file__).parent / "parser_cache" / "py_parser.py")
    parser_cls = generate_parser(grammar, source_path, "parse_string", source_name=str(grammar_path))

    return parser_cls
