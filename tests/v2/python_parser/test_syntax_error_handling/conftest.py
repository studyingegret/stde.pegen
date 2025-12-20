# See https://docs.pytest.org/en/stable/example/nonpython.html

#from functools import partial
import random
import sys
import pytest
from types import SimpleNamespace
from typing import Any, List
#import _pytest
from _pytest.python import Function

def pytest_pycollect_makeitem(collector: pytest.Module | pytest.Class, name: str, obj: object) -> Any:
    print(f"> {name} {obj} {collector.obj=} {collector=}")
    #if callable(obj) and isinstance(collector, pytest.Module):
    if hasattr(obj, "__iter__"):
        def change_name(x):
            x.name += "aaa"
            return x

        # Hell of a hack to create a function on the fly
        # Why doesn't pytest officially(?) support this?? QaQ.

        # Function wants to check the signature so I'll not use partial (XXX:?)
        def run_data(
            python_parse_file,
            python_parse_str,
            tmp_path,
            request,
            hello,
        ):
            print(hello, request.node)
            parse_invalid_syntax(
                python_parse_file,
                python_parse_str,
                tmp_path,
                *obj  #type:ignore
            )

        # May also work, kept it here just in case
        #class FunctionHack(Function):
        #    def _getobj(self):
        #        return run_data

        # This reach-in is necessary to get the right object passed to pytest.Function
        # We'll not use `with`, because if this code fails, we don't want to
        # run tests anyway (XXX:?)
        # (Another solution I can think of is to patch _pytest.python.Function with FunctionHack)
        original_obj = collector.obj
        collector.obj = SimpleNamespace({name: run_data})
        oh_jesus_my_dear_precious_functions_i_love_you = list(
            map(change_name, collector._genfunctions(name, run_data)))
        collector.obj = original_obj
        return oh_jesus_my_dear_precious_functions_i_love_you
    return None

@pytest.fixture
def hello():
    print(random.choice(["hello", "你好", "Bonjour", "konichiwa (sorry, i don't have a Japanese IME)"]))
    return "hello"

#def run_data(
#    python_parse_file,
#    python_parse_str,
#    tmp_path,
#    request,
#    hello,
#    data: List,
#):
#    print(hello, request.node)
#    parse_invalid_syntax(
#        python_parse_file,
#        python_parse_str,
#        tmp_path,
#        *data
#    )

def parse_invalid_syntax(
    python_parse_file,
    python_parse_str,
    tmp_path,
    source,
    message,
    start,
    end,
    exc_cls=SyntaxError,
    min_python_version=(3, 10),
) -> None:
    # Check we obtain the expected error from Python
    try:
        exec(source, {}, {})
    except exc_cls as py_e:
        py_exc = py_e
    except Exception as py_e:
        assert (
            False
        ), f"Python produced {py_e.__class__.__name__} instead of {exc_cls.__name__}: {py_e}"
    else:
        assert False, f"Python did not throw any exception, expected {exc_cls}"

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
