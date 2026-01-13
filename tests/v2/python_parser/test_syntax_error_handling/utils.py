

from dataclasses import dataclass
import sys, pytest
from typing import Dict, List, NamedTuple, Optional, Tuple, Type

from _pytest.mark import ParameterSet

class Testcases:
    def __new__(cls,
        items: List[Tuple],
        source: Optional[str] = None,
        exc_cls: Optional[Type] = SyntaxError,
        message: Optional[str] = None,
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        min_python_version: Optional[Tuple[int, int]] = (3, 10),
        marks = ()
    ):
        return super().__new__(cls)

    @classmethod
    def builder(cls):
        return _Builder()

    @classmethod
    def with_marks(cls, marks) -> "_Builder":
        return _Builder().with_marks(marks)

    @classmethod
    def with_args(cls, **kwargs) -> "_Builder":
        return _Builder().with_args(**kwargs)

    def __init__(self,
        items: List[Tuple],
        source: Optional[str] = None,
        exc_cls: Optional[Type] = SyntaxError,
        message: Optional[str] = None,
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        min_python_version: Optional[Tuple[int, int]] = (3, 10),
        marks = ()
    ):
        self.items = items
        self.overrides = {}
        self.marks = marks
        if source is not None:
            self.overrides[0] = source
        if exc_cls is not None:
            self.overrides[1] = exc_cls
        if message is not None:
            self.overrides[2] = message
        if start is not None:
            self.overrides[3] = start
        if end is not None:
            self.overrides[4] = end
        if min_python_version is not None:
            self.overrides[5] = min_python_version

    def __iter__(self):
        for item in self.items:
            if isinstance(item, ParameterSet):
                yield item._replace(values=fill_overrides(item.values, self.overrides))
            else:
                yield fill_overrides(item, self.overrides)

    def __repr__(self):
        return f"Testcases(items={self.items}, overrides={self.overrides}, marks={self.marks})"

class _Builder(NamedTuple):
    marks = ()
    source: Optional[str] = None
    exc_cls: Optional[Type] = SyntaxError
    message: Optional[str] = None
    start: Optional[Tuple[int, int]] = None
    end: Optional[Tuple[int, int]] = None
    min_python_version: Optional[Tuple[int, int]] = (3, 10)

    def with_marks(self, marks):
        self.marks = marks
        return self
    def with_args(self, **kwargs):
        #self.__dict__.update(kwargs) #...
        return self._replace(**kwargs)
    def create(self, items):
        return Testcases(
            items=items,
            source=self.source,
            message=self.message,
            start=self.start,
            end=self.end,
            exc_cls=self.exc_cls,
            min_python_version=self.min_python_version,
            marks=self.marks,
        )

def fill_overrides(x, overrides: Dict) -> Tuple:
    assert len(x) + len(overrides) == 6, "Total number of items mismatch"
    ret = list(x)
    ninserted = 0
    for i, v in sorted(overrides.items(), key=lambda x: x[0]):
        ret.insert(i + ninserted, v)
        ninserted += 1
    return tuple(ret)

if __name__ == "__main__":
    testcases = Testcases([
        (
            "f'a = {}'",
            (
                "valid expression required before '}'"
                if sys.version_info >= (3, 12)
                else "f-string: empty expression not allowed"
            ),
            (1, 8) if sys.version_info >= (3, 12) else None,
            (1, 9) if sys.version_info >= (3, 12) else None,
        ),
        (
            "f'a = {=}'",
            (
                "expression required before '='"
                if sys.version_info >= (3, 11)
                else "f-string: empty expression not allowed"
            ),
            (1, 8) if sys.version_info >= (3, 12) else None,
            (1, 9) if sys.version_info >= (3, 12) else None,
        ),
    ])

    for case in testcases:
        print(case)