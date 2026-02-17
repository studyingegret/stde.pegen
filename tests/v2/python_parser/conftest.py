""""Conftest for pure python parser."""

from pathlib import Path
import pytest
from importlib.util import spec_from_file_location, module_from_spec
from typing import Any
from stde.pegen.v2.build import generate_code_from_file, load_grammar_from_file
from stde.pegen.utils import PathLike

GRAMMAR_PATH = Path(__file__) / "../../../../data/python_v2.gram"
SOURCE_PATH = Path(__file__) / "../parser_cache/py_parser.py"

def _import_file(full_name: str, path: PathLike) -> Any:
    """Import a python module from a path"""
    spec = spec_from_file_location(full_name, path) #type:ignore #XXX: typeshed bug?
    assert spec
    assert spec.loader is not None
    mod = module_from_spec(spec)
    # See https://docs.python.org/3/reference/import.html?highlight=exec_module#loading
    spec.loader.exec_module(mod)
    return mod

_module: Any = None

@pytest.fixture(scope="session")
def python_parser_module(pytestconfig) -> Any:
    #raise
    if pytestconfig.option.cache_v2_python_parser:
        global _module
        if _module is None:
            generate_code_from_file(GRAMMAR_PATH, SOURCE_PATH)
            _module = _import_file(SOURCE_PATH.stem, SOURCE_PATH)
        return _module
    generate_code_from_file(GRAMMAR_PATH, SOURCE_PATH)
    return _import_file(SOURCE_PATH.stem, SOURCE_PATH)

@pytest.fixture(scope="session")
def python_parser_cls(python_parser_module) -> Any:
    return python_parser_module.PythonParser

@pytest.fixture(scope="session")
def python_parse_file(python_parser_module) -> Any:
    return python_parser_module.parse_file

@pytest.fixture(scope="session")
def python_parse_str(python_parser_module) -> Any:
    return python_parser_module.parse_string

#def pytest_runtest_call(item: pytest.Item) -> None:
#    print("::", item)