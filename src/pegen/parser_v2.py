import argparse
import ast
from functools import partial, wraps
import sys
import time
import token
import tokenize
import traceback
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Optional, Self, TextIO, Tuple, Type, TypeAlias, TypeVar, cast

from pegen.tokenizer import AbstractTokenizer, Tokenizer

from pegen.tokenizer import exact_token_types

T = TypeVar("T")
P = TypeVar("P", bound="DefaultParser") #TODO
F = TypeVar("F", bound=Callable[..., Any])

# Tokens added in Python 3.12
FSTRING_START = getattr(token, "FSTRING_START", None)
FSTRING_MIDDLE = getattr(token, "FSTRING_MIDDLE", None)
FSTRING_END = getattr(token, "FSTRING_END", None)


def logger(method: F) -> F:
    """For non-memoized functions that we want to be logged.

    (In practice this is only non-leader left-recursive functions.)
    """
    method_name = method.__name__

    @wraps(method)
    def logger_wrapper(self: P, *args: object) -> F:
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
    def memoize_wrapper(self: P, *args: object) -> F:
        mark = self.mark()
        key = mark, method_name, args
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


def memoize_left_rec(method: Callable[[P], Optional[T]]) -> Callable[[P], Optional[T]]:
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    @wraps(method)
    def memoize_left_rec_wrapper(self: P) -> Optional[T]:
        mark = self.mark()
        key = mark, method_name, ()
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
            self._cache[key] = None, mark
            lastresult, lastmark = None, mark
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

    # Should be an associated type (like Rust's) but this is the nearest thing I know
    Mark: TypeAlias = Any

    # Cooperation with decorators above
    # XXX: Might be incomplete
    _verbose: bool
    _vprint: Callable[..., Any] # Should have the same signature as print() #XXX: How to type this?
    _cache: Dict[Tuple[Mark, str, Tuple[Any, ...]], Tuple[Any, Mark]] = {}
    _level: int
    in_recursive_rule: int

    # Cooperation with python_generator_v2.py
    # XXX: There are more coupling cooperations to reveal
    call_invalid_rules: bool

    def __init__(self, *, verbose_stream: Optional[TextIO] = sys.stdout):
        self._verbose = verbose_stream is not None
        if self._verbose:
            self._vprint = partial(print, file=verbose_stream)
        self._level = 0
        Mark: TypeAlias = int #pyright:ignore
        self._cache = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # Are we looking for syntax error ? When true enable matching on invalid rules
        self.call_invalid_rules = False

    @classmethod
    @abstractmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> "BaseParser": ...

    @classmethod
    @abstractmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> "BaseParser": ...

    #@abstractmethod
    def start(self) -> Any:
        """Expected grammar entry point.

        This is not strictly necessary but is assumed to exist in most utility
        functions consuming parser instances.

        """
        pass

    @abstractmethod #XXX: ??
    def showpeek(self) -> str: ...

    @abstractmethod
    def mark(self) -> Mark: ...

    @abstractmethod
    def reset(self, index: Mark) -> None: ...

    @abstractmethod
    def diagnose(self) -> Any: ...

    @memoize
    @abstractmethod
    def match_string(self, s: str) -> Optional[Any]: ...

    #@memoize
    #@abstractmethod
    #def expect(self, *args: Any, **kwargs: Any) -> Optional[Any]: ...

    def force(self, res: Any, expectation: str) -> Optional[Any]:
        if res is None:
            raise self.make_syntax_error(f"expected {expectation}")
        return res

    def positive_lookahead(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Calls func once and does not advance."""
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return ok

    def negative_lookahead(self, func: Callable[..., object], *args: Any, **kwargs: Any) -> bool:
        """Calls func once; return value is false-ish <=> negative lookahead matches"""
        mark = self.mark()
        ok = func(*args)
        self.reset(mark)
        return not ok

    #XXX: ?
    @abstractmethod
    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        tok = self.diagnose() #?
        return SyntaxError(message, (filename, tok.start[0], 1 + tok.start[1], tok.line))


class DefaultParser(BaseParser):
    Mark: TypeAlias = int

    # Convenience method (?)
    @classmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> Self:
        return cls(Tokenizer.from_text(text), *args, **kwargs)

    @classmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> Self:
        return cls(Tokenizer.from_stream(stream), *args, **kwargs)

    def __init__(self, tokenizer: Tokenizer, *, verbose_stream: Optional[TextIO] = sys.stdout):
        self._tokenizer = tokenizer
        self._verbose = verbose_stream is not None
        if self._verbose:
            self._vprint = partial(print, file=verbose_stream)
        self._level = 0
        Mark: TypeAlias = int #pyright:ignore
        self._cache: Dict[Tuple[Mark, str, Tuple[Any, ...]], Tuple[Any, Mark]] = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # Are we looking for syntax error ? When true enable matching on invalid rules
        self.call_invalid_rules = False

    def mark(self) -> Mark:
        return self._tokenizer.mark()

    def reset(self, index: Mark) -> None:
        return self._tokenizer.reset(index)

    def showpeek(self) -> str:
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    @memoize
    def expect(self, type: str) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if (tok.string == type
         or (type in exact_token_types and tok.type == exact_token_types[type])
         or (type in token.__dict__ and tok.type == token.__dict__[type])
         or (tok.type == token.OP and tok.string == type)):
            return self._tokenizer.getnext()
        return None

    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        tok = self._tokenizer.diagnose()
        return SyntaxError(message, (filename, tok.start[0], 1 + tok.start[1], tok.line))


class CharBasedParser(BaseParser):
    Mark: TypeAlias = int

    @classmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> Self:
        return cls(text, *args, **kwargs)

    @classmethod
    def from_stream(cls, stream: TextIO, *args: Any, **kwargs: Any) -> Self:
        #stream.seek(0) #XXX: ?
        return cls(stream.read(), *args, **kwargs) #type:ignore # (?)

    def __init__(self, text: str, *, verbose_stream: Optional[TextIO] = sys.stdout):
        self._text = text
        self._pos = 0
        self._line = 0
        self._col = 0
        self._lineindex_table = ...
        self._verbose = verbose_stream is not None
        if self._verbose:
            self._vprint = partial(print, file=verbose_stream)
        self._level = 0
        Mark: TypeAlias = int #pyright:ignore
        self._cache: Dict[Tuple[Mark, str, Tuple[Any, ...]], Tuple[Any, Mark]] = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # Are we looking for syntax error ? When true enable matching on invalid rules
        self.call_invalid_rules = False

    def mark(self) -> Mark:
        return self._pos

    def reset(self, index: Mark) -> None:
        self._pos = index

    def peek(self):
        ...

    def showpeek(self) -> str: ...
        #return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    def diagnose(self) -> Any: ...

    @memoize
    def match_string(self, s: str) -> Optional[str]:
        return s if self._text.startswith(s, self._pos) else None

    @memoize
    def expect(self, type: str) -> Optional[tokenize.TokenInfo]:
        ...

    def make_syntax_error(self, message: str, filename: str = "<unknown>") -> SyntaxError:
        tok = self.diagnose()
        return SyntaxError(message, (filename, tok.start[0], 1 + tok.start[1], tok.line))


#? How to change this?
def simple_parser_main(parser_class: Type[DefaultParser]) -> None:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-v", "--verbose", action="count", default=0,
                           help="Print timing stats; repeat for more debug output")
    argparser.add_argument("-q", "--quiet", action="store_true",
                           help="Don't print the parsed program")
    argparser.add_argument("-r", "--run", action="store_true",
                           help="Run the parsed program")
    argparser.add_argument("filename",
                           help="Input file ('-' to use stdin)")

    args = argparser.parse_args()
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
        tokengen = tokenize.generate_tokens(file.readline)
        tokenizer = Tokenizer(tokengen, verbose_stream=sys.stdout if verbose_tokenizer else None)
        parser = parser_class(tokenizer, verbose_stream=sys.stdout if verbose_parser else None)
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
        diag = tokenizer.diagnose()
        nlines = diag.end[0]
        if diag.type == token.ENDMARKER:
            nlines -= 1
        print(f"Total time: {dt:.3f} sec; {nlines} lines", end="")
        if endpos:
            print(f" ({endpos} bytes)", end="")
        if dt:
            print(f"; {nlines / dt:.0f} lines/sec")
        else:
            print()
        print("Caches sizes:")
        print(f"  token array : {len(tokenizer._tokens):10}")
        print(f"        cache : {len(parser._cache):10}")
        ## print_memstats()
