import io
from contextlib import contextmanager
from typing import Any, Protocol, TextIO, Union
from collections.abc import Iterator

class PathLike(Protocol):
    """Essentially os.PathLike, except that it's a typing.Protocol, not an abstract class."""
    # https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html#standard-duck-types
    # https://mypy.readthedocs.io/en/stable/protocols.html

    def __fspath__(self) -> Union[str, bytes]: ...


# A text file or a file path.
File = Union[str, bytes, PathLike, TextIO]


@contextmanager
def open_file(file_or_path: File, mode: str = "r", *args: Any, **kwargs: Any) -> Iterator[TextIO]:
    """Smooths working on a file specified by
    - an opened file (requires TextIO), or
    - path to open (requires __fspath__()).
    """
    # From https://stackoverflow.com/questions/6783472/python-function-that-accepts-file-object-or-path
    if isinstance(file_or_path, TextIO):
        if "r" in mode and not file_or_path.readable():
            raise ValueError("Recieved unreadable stream when a readable stream is expected")
        if "w" in mode and not file_or_path.writable():
            raise ValueError("Recieved unwritable stream when a writeable stream is expected")
        yield file_or_path
    else:
        # Pylance's typing store of open() uses the abstract class os.PathLike
        if "b" in mode:
            raise ValueError("Only text mode is accepted")
        with open(file_or_path, mode, *args, **kwargs) as f: #type:ignore
            yield f #type:ignore