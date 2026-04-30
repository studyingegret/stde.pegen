#TODO:Typing

from dataclasses import dataclass, field
import dataclasses
import sys
#import pytest
from typing import TYPE_CHECKING, Any, Dict, Iterable, Iterator, List, Optional, Self, Sequence, Tuple, Type, Union
from pytest import Mark as _Mark, MarkDecorator

from _pytest.mark import ParameterSet

ExceptionType = Type[BaseException]
# By default, tuple[A] expects a single item A
Item = Tuple[Any, ...]
Mark = Union[MarkDecorator, _Mark, Iterable[Union[MarkDecorator, _Mark]]]
#Marks = List[Mark]

@dataclass
class Testcases:
    # Tell pytest this is not a test class, although its name starts with "Test"
    # Silences "PytestCollectionWarning: cannot collect test class 'Testcases' because it has a __init__ constructor"
    __test__ = False

    #XXX: ? (these are AI-generated)
    #  Fields without default values must come first
    # items: List[Item]
    #  Fields with default values
    # overrides: Dict[int, Any] = field(default_factory=dict)
    # marks: MarkType = ()

    # Note: Actually unneccessary, I don't know why I want to keep it
    # Might be removed in the future?
    def __new__(cls,
        items: List[Item],
        source: Optional[str] = None,
        exc_cls: Optional[ExceptionType] = SyntaxError,
        message: Optional[str] = None,
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        min_python_version: Optional[Tuple[int, int]] = (3, 10),
        marks: List[Mark] = []
    ) -> "Testcases":
        return super().__new__(cls)

    @classmethod
    def builder(cls) -> "_Builder":
        return _Builder()

    @classmethod
    def with_marks(cls, marks: List[Mark]) -> "_Builder":
        return _Builder().with_marks(marks)

    @classmethod
    def with_args(cls, **kwargs: Any) -> "_Builder":
        return _Builder().with_args(**kwargs)

    def __init__(self,
        items: List[Item],
        source: Optional[str] = None,
        exc_cls: Optional[ExceptionType] = SyntaxError,
        message: Optional[str] = None,
        start: Optional[Tuple[int, int]] = None,
        end: Optional[Tuple[int, int]] = None,
        min_python_version: Optional[Tuple[int, int]] = (3, 10),
        marks: List[Mark] = []
    ) -> None:
        self.items = items
        self.overrides: Dict[int, Any] = {}
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

    def __iter__(self) -> Iterator[Union[ParameterSet, Item]]:
        for item in self.items:
            if isinstance(item, ParameterSet):
                yield item._replace(values=fill_overrides(item.values, self.overrides))
            else:
                yield fill_overrides(item, self.overrides)

    def __repr__(self) -> str:
        return f"Testcases(items={self.items}, overrides={self.overrides}, marks={self.marks})"

@dataclass
class _Builder:
    marks: List[Mark] = field(default_factory=list)
    source: Optional[str] = None
    exc_cls: Optional[ExceptionType] = SyntaxError
    message: Optional[str] = None
    start: Optional[Tuple[int, int]] = None
    end: Optional[Tuple[int, int]] = None
    min_python_version: Optional[Tuple[int, int]] = (3, 10)

    def with_marks(self, marks: List[Mark]) -> Self:
        self.marks = marks
        return self
    def with_args(self, **kwargs: Any) -> Self:
        #self.__dict__.update(kwargs) #...
        return dataclasses.replace(self, **kwargs)

    def create(self, items: List[Item]) -> Testcases:
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

def fill_overrides(x: Sequence[Any], overrides: Dict[int, Any]) -> Tuple[Any, ...]:
    assert len(x) + len(overrides) == 6, "Total number of items mismatch"
    ret = list(x)
    ninserted = 0
    for i, v in sorted(overrides.items(), key=lambda x: x[0]):
        ret.insert(i + ninserted, v)
        #ninserted += 1
    return tuple(ret)

if __name__ == "__main__":
    if not TYPE_CHECKING:
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
            
        print(fill_overrides(("def f(a, *):\n\tpass", (1, 10), (1, 11)), {1: "aaa", 2:"bbb", 3:"ccc"}))
        
        t = Testcases.with_args(message="a").create([("def f(a, *):\n\tpass", (1, 10), (1, 11))])
        assert list(t)[0] == ('def f(a, *):\n\tpass', SyntaxError, 'a', (1, 10), (1, 11), (3, 10)), list(t)[0]