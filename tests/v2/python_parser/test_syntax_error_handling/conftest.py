# See https://docs.pytest.org/en/stable/example/nonpython.html
#TODO:Typing
import pathlib
from pprint import pprint
import sys
import pytest
import re
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Tuple, Type
from .utils import Testcases
from _pytest.mark import ParameterSet


def_linenos_k = pytest.StashKey[Dict[str, int]]()


def pytest_pycollect_makemodule(module_path: pathlib.Path, parent: pytest.Collector) -> pytest.Module:# | None:
    module = pytest.Module.from_parent(parent, path=module_path)
    module.stash[def_linenos_k] = read_def_linenos(module_path)
    return module

def read_def_linenos(path: pathlib.Path) -> Dict[str, int]:
    linenos: Dict[str, int] = {}
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if m := re.match(r"\s*(test_[\w\d]+)\s*=", line):
                name = m[1]
                if name in linenos:
                    print(f"Warning: redefinition of {name} on line {lineno} "
                          f"(previously defined on line {linenos[name]})")
                linenos[name] = lineno
    return linenos

def pytest_pycollect_makeitem(collector: pytest.Module | pytest.Class, name: str, obj: object) -> Any:
    if isinstance(obj, Testcases):
        print("::", obj)
        pprint(list(obj))

        # Hell of a hack to create a function on the fly
        # Why doesn't pytest officially(?) support this?? QaQ.

        _label_fn = lambda ix: (
            f"{ix[0]}-{ix[1][0]}" #type:ignore
            if _expects_syntax_error(ix[1]) #type:ignore
            else f"{ix[0]}-{ix[1][0]}-{_expects_exc_name(ix[1])}" #type:ignore
        )
        parameterize = pytest.mark.parametrize(
            "source, exc_cls, message, start, end, min_python_version",
            obj, #type:ignore
            ids=list(map(_label_fn, enumerate(obj))) #type:ignore
        )

        # Set the lineno so that IDEs' "Go to definition" goes to the right lineno
        # instead of the lineno of definition of run_data (in run_data_factory)
        if name not in collector.stash[def_linenos_k]:
            print(f"Warning: lineno of {name} not collected for {collector.path} ({collector=!r})")
        fn = run_data_factory(firstlineno=collector.stash[def_linenos_k][name])  #type:ignore
        fn = parameterize(fn)
        for mark in reversed(obj.marks):
            fn = mark(fn) #type:ignore #XXX: pytest.Mark not callable?

        # This reach-in is necessary to get the right object passed to pytest.Function
        # We'll not use `with`, because if this code fails, we don't want to
        # run tests anyway (XXX:?)
        # (Another solution I can think of is to patch
        # _pytest.python.Function with FunctionHack, see below)
        original_obj = collector.obj
        collector.obj = SimpleNamespace({name: fn})
        oh_jesus_my_dear_precious_functions_i_love_you = list(collector._genfunctions(name, fn))
        collector.obj = original_obj
        return oh_jesus_my_dear_precious_functions_i_love_you
    return None

def _expects_exc_name(x):
    return (x.values[1] if isinstance(x, ParameterSet) else x[1]).__name__ #pyright:ignore

def _expects_syntax_error(x):
    return _expects_exc_name(x) == "SyntaxError"

# XXX:?
# pytest complains `duplicate parametrization of 'source'` even with copy.deepcopy.
# It seems that even after copy.deepcopy the function is still the same instance.
# So a factory is neccessary.
def run_data_factory(firstlineno: int = 1) -> Callable[..., None]:
    # Note that `pytest.Function` wants to check the argument names in the signature.
    def run_data(
        python_parse_file,
        python_parse_str,
        tmp_path,
        source: str,
        exc_cls: Type[BaseException],
        message: str,
        start: Tuple[int, int],
        end: Tuple[int, int],
        min_python_version: Tuple[int, int],
        pytestconfig,
    ):
        parse_invalid_syntax(
            python_parse_file,
            python_parse_str,
            tmp_path,
            source,
            exc_cls,
            message,
            start,
            end,
            min_python_version,
            pytestconfig,
        )
    run_data.__code__ = run_data.__code__.replace(co_firstlineno=firstlineno)
    return run_data

# May also work, kept it here just in case
#class FunctionHack(Function):
#    def _getobj(self):
#        return run_data

def parse_invalid_syntax(
    python_parse_file,
    python_parse_str,
    tmp_path,
    source,
    exc_cls,
    message,
    start,
    end,
    min_python_version,
    pytestconfig,
) -> None:
    verbose_tokenizer_stream = sys.stdout if pytestconfig.option.v2_python_parser_verbose_tokenizer else None
    verbose_parser_stream = sys.stdout if pytestconfig.option.v2_python_parser_verbose_parser else None

    # Check we obtain the expected error from Python
    try:
        exec(source, {}, {})
    except exc_cls as py_e:
        py_exc = py_e
    except Exception as py_e:
        assert (
            False
        ), f"Python produced {py_e!r} instead of {exc_cls.__name__}({message!r})"
    else:
        assert False, ("Python did not throw any exception, expected "
                       f"{exc_cls.__name__}({message!r})")

    # Check our parser raises both from str and file mode.
    with pytest.raises(exc_cls) as e:
        # XXX stdout or stderr?
        python_parse_str(source, "exec",
                         verbose_tokenizer_stream=verbose_tokenizer_stream,
                         verbose_parser_stream=verbose_parser_stream)

    assert_exc_has_message(message, e)

    test_file = tmp_path / "test.py"
    with open(test_file, "w") as f:
        f.write(source)

    with pytest.raises(exc_cls) as e:
        python_parse_file(str(test_file),
                          verbose_tokenizer_stream=verbose_tokenizer_stream,
                          verbose_parser_stream=verbose_parser_stream)

    # Check Python message but do not expect message to match for earlier Python versions
    if sys.version_info >= min_python_version:
        # This fails for Python < 3.10.5 but keeping the fix for a patch version is not
        # worth it
        assert message in py_exc.args[0]

    assert_exc_has_message(message, e)

    if start is None:
        return

    # Check start/end line/column on Python 3.10
    for parser_name, exc in ([("Python", py_exc)] if sys.version_info >= min_python_version else []) + [
        ("pegen", e.value)
    ]:
        if (
            exc.lineno != start[0]
            or exc.offset != start[1]
            # Do not check end for indentation errors
            or (
                sys.version_info >= (3, 10)
                and not isinstance(e, IndentationError)
                and exc.end_lineno != end[0]
            )
            or (
                sys.version_info >= (3, 10)
                and not isinstance(e, IndentationError)
                and (end[1] is not None and exc.end_offset != end[1])
            )
        ):
            if sys.version_info >= (3, 10):
                raise ValueError(
                    f"Expected locations of {start} and {end}, but got "
                    f"{(exc.lineno, exc.offset)} and {(exc.end_lineno, exc.end_offset)} "
                    f"from {parser_name}"
                )
            else:
                raise ValueError(
                    f"Expected locations of {start}, but got "
                    f"{(exc.lineno, exc.offset)} from {parser}"
                )

def assert_exc_has_message(message, exc_info) -> None:
    if message not in (exc_str := str(exc_info.exconly())):
        print(exc_str)
    assert message in exc_str