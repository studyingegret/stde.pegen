# See https://docs.pytest.org/en/stable/example/nonpython.html
#TODO:Typing
from pprint import pprint
import sys
import pytest
from types import SimpleNamespace
from typing import Any, List, Tuple, Type
from .utils import Testcases
from _pytest.mark import ParameterSet


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
        fn = run_data_factory()
        fn = parameterize(fn)
        for mark in reversed(obj.marks):
            fn = mark(fn)

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
def run_data_factory():
    # Note that `pytest.Function` wants to check the signature.
    def run_data(
        python_parse_file,
        python_parse_str,
        tmp_path,
        source: str,
        exc_cls: Type,
        message: str,
        start: Tuple[int, int],
        end: Tuple[int, int],
        min_python_version: Tuple[int, int]
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
            min_python_version
        )
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
) -> None:
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
        python_parse_str(source, "exec")

    print(str(e.exconly()))
    assert message in str(e.exconly())

    test_file = tmp_path / "test.py"
    with open(test_file, "w") as f:
        f.write(source)

    with pytest.raises(exc_cls) as e:
        python_parse_file(str(test_file))

    # Check Python message but do not expect message to match for earlier Python versions
    if sys.version_info >= min_python_version:
        # This fails for Python < 3.10.5 but keeping the fix for a patch version is not
        # worth it
        assert message in py_exc.args[0]

    print(str(e.exconly()))
    assert message in str(e.exconly())

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
