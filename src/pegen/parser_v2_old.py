import argparse
import ast
from enum import Enum, IntEnum
from functools import partial, wraps
import sys
import time
import token
import tokenize
import traceback
from abc import ABC, abstractmethod
from typing import (TYPE_CHECKING, Any, Callable, ClassVar, Dict, Final, Generic, List, Literal, NamedTuple, Never, Optional,
                    Self, TextIO, Tuple, Type, TypeAlias, TypeVar, Union, cast, Protocol, overload)

from pegen.tokenizer import Tokenizer
from pegen.tokenizer import exact_token_types

T = TypeVar("T")
#T2 = TypeVar("T2", default=Any, covariant=True) #?
T2 = TypeVar("T2", default=Any)
F = TypeVar("F", bound=Callable[..., Any])

## Tokens added in Python 3.12
#FSTRING_START = getattr(token, "FSTRING_START", None)
#FSTRING_MIDDLE = getattr(token, "FSTRING_MIDDLE", None)
#FSTRING_END = getattr(token, "FSTRING_END", None)

"""
/*enum RuleResult<T, E> {
    Success(T)
    Failure(E)
}*/
"""
"""
enum RuleResult<T> {
    Success(T)
    Failure
}
"""


class RuleValue(IntEnum):
    NONE = 0
    FAILURE = 1

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self._name_}"


if TYPE_CHECKING:
    # Type checker defects are annoying sdfiajioioshdf!!!

    class _Base(NamedTuple, Generic[T2]):
        # Need to fake defaults or Pyright complains (should be Pyright defect)
        ok: bool = True
        """Whether the rule succeeded."""
        value: T2 = cast(T2, None)
        """The value of the rule.

        It is `RuleValue.NONE` if the rule is `node?` and didn't match `node`.
        It may also be `RuleValue.NONE` if e.g. the rule is $ (ENDMARKER), etc. (?)

        It is `RuleValue.FAILURE` if `ok` == False.

        Note: Though from the above text, it can be deduced that
        its type is actually Union[T2, RuleValue], it is typed as T2 for convenience.
        In usage, check `ok` and possibly check `value` against `RuleValue.NONE`.
        """

        def __bool__(self):
            return self.ok

        @classmethod
        #def from_bool(cls, value: bool) -> "_Base[Literal[RuleValue.NONE]]":
        def from_bool(cls, value: bool) -> "_Base[Any]": # Feels easier
            """Return success(RuleValue.NONE) if value is True, else failure()
            (failure[Any]()).
            """
            return cast("_Base", None)

    # success and failure would be much simpler if we could use
    # parameterized functions
    # -- No. Parameterized functions in Python 3.12 still don't work with
    #    the subscript notation. This is a trouble because failure doesn't
    #    have a source of T2 from arguments, it has to be supplied
    #    via e.g. generics, and that means creating a new class.
    class success(_Base[T2]):
        ok: Literal[True] #type:ignore

        @overload
        def __new__(cls, value: T2) -> "success[T2]": ...
        # mypy bug?
        # mypy: Incompatible return type for "__new__" (returns "success[Literal[RuleValue.NONE]]",
        #       but must return a subtype of "success[Any]")
        @overload
        #def __new__(cls) -> "success[Literal[RuleValue.NONE]]": ... #type:ignore
        def __new__(cls) -> "success[T2]": ...

        # Need to specify __new__ or Pyright deduces wrongly (should be Pyright defect)
        #
        # mypy bug?
        # mypy: Incompatible return type for "__new__" (returns "success[T2 | Literal[RuleValue.NONE]]",
        #       but must return a subtype of "success[Any]")
        def __new__(cls, value: T2 = cast(T2, RuleValue.NONE)) -> "success[T2]": #type:ignore
            #return cast("success", super().__new__(cls, True, value))
            return cast("success[T2]", None)

        # Overloads also needed for __init__
        # since because __new__ returns instance of current class,
        # type checkers assume __init__ is also called
        @overload
        def __init__(self, value: T2): ...
        @overload
        def __init__(self): ...
        # Need to fake a default in __init__ or mypy and Pyright complain wrongly
        def __init__(self, value: T2 = cast(T2, RuleValue.NONE)):
            # mypy: Too many arguments for "__init__" of "object" (mypy bug?)
            super().__init__(True, value)  #type:ignore

    #reveal_type(success()) # Expect success[Literal[RuleValue.NONE]] but mypy says success[Any]
    #reveal_type(success().value) # Expect Literal[RuleValue.NONE] but mypy says Any
    reveal_type(success()) # Expect success[Any] (Feels easier)
    reveal_type(success().value) # Expect Any (Feels easier)
    # For now I won't take time to fix 2 mypy discrepancies above
    reveal_type(success(1.2)) # Expect success[float]
    reveal_type(success(1.2).value) # Expect float
    #reveal_type(success[int].value) # Expect int


    class failure(_Base[T2]):
        ok: Literal[False]  #type:ignore

        # Interestingly, no need to specify __new__ here, Pyright gives no false negatives

        # `-> None` is necessary or mypy says "Call to untyped function "failure" in typed context"
        # might be a mypy bug
        def __init__(self) -> None:
            # mypy: Too many arguments for "__init__" of "object" (mypy bug?)
            super().__init__(True, cast(T2, RuleValue.FAILURE))  #type:ignore


    RuleResult = _Base[T2]
else:
    # The same, without type checker magic

    class RuleResult(NamedTuple):
        ok: bool
        """Whether the rule succeeded."""
        value: Any  # Type doesn't have to be known at definition time
        """The value of the rule.

        It is RuleValue.NONE if the rule is `node?` and didn't match `node`.

        It is RuleValue.FAILURE if ok == False.
        """

        def __class_getitem__(_):
            return RuleResult

        def __bool__(self):
            return self.ok

        @classmethod
        def from_bool(cls, value: bool) -> "RuleResult[Literal[RuleValue.NONE]]":
            """Return success(RuleValue.NONE) if value is True, else failure()
            (failure[Literal[RuleValue.NONE]]()).
            """
            return success() if value else failure()

    class success:
        # Better keep consistency with type checker version (though not needed)
        def __class_getitem__(_):
            return success

        def __new__(cls, value=RuleValue.NONE) -> RuleResult:
            return RuleResult(True, value)

    class failure:
        def __class_getitem__(_):
            return failure

        def __new__(cls) -> RuleResult:
            return RuleResult(False, RuleValue.FAILURE)


class MarkRequirements(Protocol):
    def __hash__(self) -> int: ...
    #def __eq__(self, other: Self) -> bool: ... # Pyright doesn't like this
    #def __eq__(self, other: "MarkRequirements", /) -> bool: ... # Pyright doesn't like this
    def __eq__(self, other: object, /) -> bool: ...
    def __lt__(self, other: Self, /) -> bool: ...
    def __le__(self, other: Self, /) -> bool: ...
    def __gt__(self, other: Self, /) -> bool: ...
    def __ge__(self, other: Self, /) -> bool: ...


def logger(method: F) -> F:
    """For non-memoized functions that we want to be logged.

    (In practice this is only non-leader left-recursive functions.)
    """
    method_name = method.__name__

    @wraps(method)
    def logger_wrapper(self: "BaseParser", *args: object) -> F:
        if not self._verbose:
            return method(self, *args)
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        self._vprint(f"{fill}{method_name}({argsr}) .... (looking at {self.showpeek()})")
        self._level += 1
        tree = method(self, *args)
        self._level -= 1
        self._vprint(f"{fill}... {method_name}({argsr}) --> {tree!s:.200}")
        return tree

    return cast(F, logger_wrapper)


def memoize(method: F) -> F:
    """Memoize a symbol method."""
    method_name = method.__name__

    @wraps(method)
    def memoize_wrapper(self: "BaseParser", *args: object) -> F:
        mark = self.mark()
        key = (mark, method_name, args)
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self.reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                self._vprint(f"{fill}{method_name}({argsr}) ... (looking at {self.showpeek()})")
            self._level += 1
            tree = method(self, *args)
            self._level -= 1
            if verbose:
                self._vprint(f"{fill}... {method_name}({argsr}) -> {tree!s:.200}")
            endmark = self.mark()
            self._cache[key] = tree, endmark
        else:
            tree, endmark = self._cache[key]
            if verbose:
                self._vprint(f"{fill}{method_name}({argsr}) -> {tree!s:.200}")
            self.reset(endmark)
        return tree

    return cast(F, memoize_wrapper)


def memoize_left_rec(method: Callable[["BaseParser"], RuleResult[T]]) -> Callable[["BaseParser"], RuleResult[T]]:
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    @wraps(method)
    def memoize_left_rec_wrapper(self: "BaseParser") -> RuleResult[T]:
        mark = self.mark()
        key = (mark, method_name, ())
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self.reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                self._vprint(f"{fill}{method_name} ... (looking at {self.showpeek()})")
            self._level += 1

            # For left-recursive rules we manipulate the cache and
            # loop until the rule shows no progress, then pick the
            # previous result.  For an explanation why this works, see
            # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
            # (But we use the memoization cache instead of a static
            # variable; perhaps this is similar to a paper by Warth et al.
            # (http://web.cs.ucla.edu/~todd/research/pub.php?id=pepm08).

            # Prime the cache with a failure.
            self._cache[key] = failure(), mark
            lastresult, lastmark = failure(), mark
            depth = 0
            if verbose:
                self._vprint(f"{fill}Recursive {method_name} at {mark} depth {depth}")

            while True:
                self.reset(mark)
                self.in_recursive_rule += 1
                try:
                    result = method(self)
                finally:
                    self.in_recursive_rule -= 1
                endmark = self.mark()
                depth += 1
                if verbose:
                    self._vprint(
                        f"{fill}Recursive {method_name} at {mark} depth {depth}: {result!s:.200} to {endmark}"
                    )
                if not result:
                    if verbose:
                        self._vprint(f"{fill}Fail with {lastresult!s:.200} to {lastmark}")
                    break
                if endmark <= lastmark:
                    if verbose:
                        self._vprint(f"{fill}Bailing with {lastresult!s:.200} to {lastmark}")
                    break
                self._cache[key] = lastresult, lastmark = result, endmark

            self.reset(lastmark)
            tree = lastresult

            self._level -= 1
            if verbose:
                self._vprint(f"{fill}{method_name}() -> {tree!s:.200} [cached]")
            if tree:
                endmark = self.mark()
            else:
                endmark = mark
                self.reset(endmark)
            self._cache[key] = tree, endmark
        else:
            tree, endmark = self._cache[key]
            if verbose:
                self._vprint(f"{fill}{method_name}() -> {tree!s:.200} [fresh]")
            if tree:
                self.reset(endmark)
        return tree

    return memoize_left_rec_wrapper


class BaseParser(ABC):
    """Parsing base class v2."""

    #XXX: How much of this can change depending on the exact parser type?
    KEYWORDS: ClassVar[Tuple[str, ...]]
    SOFT_KEYWORDS: ClassVar[Tuple[str, ...]]

    Mark: TypeAlias = MarkRequirements
    """Should be an associated type (like Rust's) but this is the nearest thing I know.
    Currently methods accepting Mark as argument need #type:ignore[override] because
    of the lack of associated type semantic (I think so).

    What is intended to express is that
    1. A class implementing BaseParser should define Mark to be a type,
       as a class variable
    2. "Mark" shall mean that same type and only that type

    Currently type checkers understand it as "any type that implements MarkRequirements"
    instead of "declaration only here; the same one type in implementing classes"
    leading to requiring #type:ignore[override].
    """

    # Cooperation with decorators above
    # XXX: Might be incomplete
    _verbose: bool
    _vprint: Callable[..., Any] # Should have the same signature as print() #XXX: How to type this?
    """Only present when self._verbose is True"""
    _cache: Dict[Tuple[Mark, str, Tuple[Any, ...]], Tuple[Any, Mark]] = {}
    _level: int
    in_recursive_rule: int

    # Cooperation with python_generator_v2.py
    # XXX: There are more coupling cooperations to reveal?
    call_invalid_rules: bool

    def __init__(self, *args: Any, verbose_stream: Optional[TextIO] = None, **kwargs: Any):
        self._verbose = verbose_stream is not None
        if self._verbose:
            self._vprint = partial(print, file=verbose_stream)
        self._level = 0
        self._cache = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # Are we looking for syntax error ? When true enable matching on invalid rules
        #XXX
        self.call_invalid_rules = False

    @classmethod
    @abstractmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> "BaseParser": ...

    @classmethod
    @abstractmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> "BaseParser": ...

    def start(self) -> RuleResult[Any]:
        """Expected grammar entry point.

        This is not strictly necessary but is assumed to exist in most utility
        functions consuming parser instances.

        """
        ...

    @abstractmethod #XXX: ??
    def nextpos(self) -> Tuple[int, int]:
        """Return (line, col) of next token (if tokenizing) or current position"""
    #@abstractmethod #XXX: ??
    #def nextpos_as_start_of_rule(self) -> Tuple[int, int]:
    #    return self._tokenizer.peek().start
    #@abstractmethod #XXX: ??
    #def nextpos_as_end_of_rule(self) -> Tuple[int, int]:
    #    return self._tokenizer.peek().start

    def showpeek(self) -> str:
        line, col = self.nextpos()
        return f"{line}.{col}"

    @abstractmethod
    def mark(self) -> Mark: ...

    @abstractmethod
    def reset(self, index: Mark) -> None: ...

    @abstractmethod
    def diagnose(self) -> Tuple[int, int, str]:
        """Return
        - First two items: farthest matched position (line, col) (both indcies 1-based).
        - Third item: farthest matched line, i.e. the text of the line
          whose lineno is the first item (used in error messages).
        """

    @memoize
    @abstractmethod
    def match_string(self, s: str) -> Optional[Any]: ...

    @abstractmethod
    def endmarker(self) -> RuleResult[Any]: ...

    def force(self, res: Any, expectation: str) -> Optional[Any]:
        if res is None:
            raise self.make_syntax_error(f"expected {expectation}")
        return res

    def positive_lookahead(self, func: Callable[..., RuleResult[T]], *args: Any, **kwargs: Any) -> RuleResult[T]:
        """Calls func once and does not advance."""
        mark = self.mark()
        res = func(*args, **kwargs)
        self.reset(mark)
        return res

    def negative_lookahead(self, func: Callable[..., RuleResult[T]], *args: Any, **kwargs: Any
                           ) -> RuleResult[Literal[RuleValue.NONE]]:
        """Calls func once, its return value is False-ish <=> negative lookahead will match"""
        mark = self.mark()
        res = func(*args, **kwargs)
        self.reset(mark)
        return RuleResult.from_bool(not res.ok) # TODO: This abandons result value...

    #XXX: ?
    #XXX: filename?
    @abstractmethod
    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        line, col, line_text = self.diagnose()
        return SyntaxError(message, (filename, line, col, line_text))


# Tokens added in Python 3.12
FSTRING_START = getattr(token, "FSTRING_START", None)
FSTRING_MIDDLE = getattr(token, "FSTRING_MIDDLE", None)
FSTRING_END = getattr(token, "FSTRING_END", None)


class DefaultParser(BaseParser):
    Mark: TypeAlias = int  #pyright:ignore

    # Convenience method (?)
    @classmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> Self:
        return cls(Tokenizer.from_text(text), *args, **kwargs)

    @classmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> Self:
        return cls(Tokenizer.from_stream(stream), *args, **kwargs)

    def __init__(self, tokenizer: Tokenizer, *, verbose_stream: Optional[TextIO] = None):
        super().__init__(verbose_stream=verbose_stream)
        self._tokenizer = tokenizer

    def mark(self) -> Mark:
        return self._tokenizer.mark()

    def reset(self, index: Mark) -> None: #type:ignore
        return self._tokenizer.reset(index)

    def nextpos(self) -> Tuple[int, int]:
        return self._tokenizer.peek().start

    def showpeek(self) -> str:
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]} {tok.string!r}"

    def endmarker(self) -> RuleResult[Literal[RuleValue.NONE]]:
        return RuleResult.from_bool(self._tokenizer.peek().type == token.ENDMARKER)
        #if (t := self._tokenizer.peek().type) == token.ENDMARKER:
        #    return True
        #elif t.type == token.NEWLINE:
        #    m = self.mark()
        #    self._tokenizer.getnext()

    def diagnose(self) -> Tuple[int, int, str]:
        t = self._tokenizer.diagnose()
        end_line = t.end[0]
        if t.type == token.ENDMARKER:
            end_line -= 1
        return (end_line, t.end[1], t.line)

    @memoize
    def name(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME and tok.string not in self.KEYWORDS:
            return success(self._tokenizer.getnext())
        #reveal_type(failure[tokenize.TokenInfo]()) # See Note 1 at end of file
        return failure()

    @memoize
    def number(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NUMBER:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def string(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.STRING:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def fstring_start(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == FSTRING_START:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def fstring_middle(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == FSTRING_MIDDLE:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def fstring_end(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == FSTRING_END:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def op(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.OP:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def type_comment(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.TYPE_COMMENT:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def soft_keyword(self) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME and tok.string in self.SOFT_KEYWORDS:
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def newline(self) -> RuleResult[tokenize.TokenInfo]:
        return self._expect("NEWLINE")

    @memoize
    def indent(self) -> RuleResult[tokenize.TokenInfo]:
        return self._expect("INDENT")

    @memoize
    def dedent(self) -> RuleResult[tokenize.TokenInfo]:
        return self._expect("DEDENT")

    def _expect(self, type: str) -> RuleResult[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if (tok.string == type
         or (type in exact_token_types and tok.type == exact_token_types[type])
         or (type in token.__dict__ and tok.type == token.__dict__[type])
         or (tok.type == token.OP and tok.string == type)):
            return success(self._tokenizer.getnext())
        return failure()

    @memoize
    def match_string(self, type: str) -> RuleResult[tokenize.TokenInfo]: #pyright:ignore
        tok = self._tokenizer.peek()
        if (tok.string == type
         or (type in exact_token_types and tok.type == exact_token_types[type])
         or (type in token.__dict__ and tok.type == token.__dict__[type])
         or (tok.type == token.OP and tok.string == type)):
            return success(self._tokenizer.getnext())
        return failure()

    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        tok = self._tokenizer.diagnose()
        return SyntaxError(message, (filename, tok.start[0], 1 + tok.start[1], tok.line))


def _count_nlines_and_last_col(s: str) -> Tuple[int, int]:
    """Second return item is always 0 when first return item is 0"""
    length = len(s)
    i = 0
    nlines = 0
    last_line_start = 0
    while i < length:
        if s[i] == "\n":
            i += 1
            nlines += 1
            last_line_start = i
        elif s[i] == "\r":
            i += 1
            if i < length and s[i] == "\n":
                i += 1
            nlines += 1
            last_line_start = i
        else:
            i += 1
    # If Line 1 starts at a, Line 2 starts at b, then length of Line 1 is b - a
    return (0, 0) if nlines == 0 else (nlines, length - last_line_start)

def _get_last_line(s: str) -> str:
    length = len(s)
    i = length - 1
    while i >= 0:
        #XXX: Omit empty lines?
        #XXX: Only accept "\n" as newline?
        if s[i] == "\n" or s[i] == "\r":
            return s[i+1:]
        else:
            i -= 1
    return s  # There is no newline character


class CharBasedParser(BaseParser):
    class Mark(NamedTuple):
        line: int
        col: int
        pos: int
        def __eq__(self, other: object, /) -> bool: return self[2] == other[2] #type:ignore
        def __lt__(self, other: Self, /) -> bool: return self[2] < other[2] #type:ignore
        def __le__(self, other: Self, /) -> bool: return self[2] <= other[2] #type:ignore
        def __gt__(self, other: Self, /) -> bool: return self[2] > other[2] #type:ignore
        def __ge__(self, other: Self, /) -> bool: return self[2] >= other[2] #type:ignore
        if TYPE_CHECKING: #type:ignore
            def __hash__(self) -> int: ... #type:ignore

    @classmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> Self:
        return cls(text, *args, **kwargs)

    @classmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> Self:
        #stream.seek(0) #XXX: ?
        return cls(stream.read(), *args, **kwargs)

    def __init__(self, text: str, *, verbose_stream: Optional[TextIO] = None):
        super().__init__(verbose_stream=verbose_stream)
        self._text = text
        self._pos = 0
        self._line = 0
        self._col = 0
        self._farthest = self.mark()

    def mark(self) -> Mark:
        #return Mark(self._pos, self._line, self._col) #pyright:ignore
        return self.__class__.Mark(self._pos, self._line, self._col)

    def reset(self, mark: Mark) -> None: #type:ignore
        self._pos, self._line, self._col = mark

    def nextpos(self) -> Tuple[int, int]:
        return self._line, self._col

    def diagnose(self) -> Tuple[int, int, str]:
        m = self._farthest
        return (m.line, m.col, _get_last_line(self._text))

    def endmarker(self) -> RuleResult[Literal[RuleValue.NONE]]:
        return RuleResult.from_bool(self._pos == len(self._text))

    def any_char(self) -> Optional[str]:
        if self._pos == len(self._text):
            return None
        if self._text[self._pos] == "\n":
            self._line += 1
            self._col = 0
        else:
            self._col += 1
        char = self._text[self._pos]
        self._pos += 1
        self._update_farthest(self.mark())
        return char

    @memoize
    def match_string(self, s: str) -> Optional[str]:
        if not self._text.startswith(s, self._pos):
            return None
        nlines, last_col = _count_nlines_and_last_col(s)
        self._pos += len(s)
        self._line += nlines
        self._col = last_col if nlines else self._col + len(s)
        self._update_farthest(self.mark())
        return s

    def _update_farthest(self, mark: Mark) -> None:
        self._farthest = max(mark, self._farthest)

    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        line, col, line_text = self.diagnose()
        return SyntaxError(message, (filename, line, col, line_text))


#? How to change this?
def simple_parser_main(parser_class: Type[BaseParser]) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-v", "--verbose", action="count", default=0,
                   help="Print timing stats; repeat for more debug output",)
    p.add_argument("-q", "--quiet", action="store_true",
                   help="Don't print the parsed program")
    p.add_argument("-r", "--run", action="store_true",
                   help="Run the parsed program")
    p.add_argument("filename",
                   help="Input file ('-' to use stdin)")

    args = p.parse_args()
    verbose = args.verbose
    verbose_tokenizer = verbose >= 3
    verbose_parser = verbose == 2 or verbose >= 4

    t0 = time.time()

    filename = args.filename
    if filename == "" or filename == "-":
        filename = "<stdin>"
        file = sys.stdin
    else:
        file = open(args.filename)
    try:
        parser = parser_class.from_stream(file, verbose_stream=sys.stdout if verbose_parser else None)
        tree = parser.start()
        try:
            if file.isatty():
                endpos = 0
            else:
                endpos = file.tell()
        except IOError:
            endpos = 0
    finally:
        if file is not sys.stdin:
            file.close()

    t1 = time.time()

    if tree is None:
        err = parser.make_syntax_error(filename)
        traceback.print_exception(err.__class__, err, None)
        sys.exit(1)

    if not args.quiet:
        try:
            ast_dump = ast.dump(tree)
        except TypeError:
            print("Parse result:")
            print(tree)
        else:
            print("AST dump of parse result:")
            print(ast_dump)
    if args.run:
        exec(compile(tree, filename=filename, mode="exec"))

    if verbose:
        dt = t1 - t0
        nlines = parser.diagnose()[0]
        print(f"Total time: {dt:.3f} sec; {nlines} lines", end="")
        if endpos:
            print(f" ({endpos} bytes)", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        #print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"cache : {len(parser._cache):10}")
        ## print_memstats()


"""Note 1: mypy: Revealed type is "
tuple[
    builtins.bool,
    tuple[
        builtins.int,
        builtins.str,
        tuple[builtins.int, builtins.int],
        tuple[builtins.int, builtins.int],
        builtins.str,
        fallback=tokenize.TokenInfo
    ], fallback=pegen.parser_v2.failure[
        tuple[
            builtins.int,
            builtins.str,
            tuple[builtins.int, builtins.int],
            tuple[builtins.int, builtins.int],
            builtins.str, fallback=tokenize.TokenInfo
        ]
    ]
]"
???
"""