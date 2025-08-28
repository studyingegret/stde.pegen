import io
import token
import tokenize
from weakref import finalize
from tokenize import TokenInfo
from typing import Any, Dict, Iterator, List, Optional, Self, TextIO
from abc import abstractmethod

Mark = int  # NewType('Mark', int)

exact_token_types = token.EXACT_TOKEN_TYPES


def shorttok(tok: TokenInfo) -> str:
    return "%-25.25s" % f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"


class AbstractTokenizer:
    """Abstract interface for tokenizers with position tracking and error diagnostics."""

    @classmethod
    @abstractmethod
    def from_text(cls, text: str, *args: Any, **kwargs: Any) -> "AbstractTokenizer": ...

    @classmethod
    @abstractmethod
    def from_stream(cls, file: TextIO, *args: Any, **kwargs: Any) -> "AbstractTokenizer": ...

    @abstractmethod
    def getnext(self) -> TokenInfo:
        """Return next valid token, advancing position."""

    @abstractmethod
    def peek(self) -> TokenInfo:
        """Return next valid token without advancing position."""

    @abstractmethod
    def diagnose(self) -> TokenInfo:
        """Return last token for error reporting (that token is likely the cause of error)."""

    @abstractmethod
    def mark(self) -> int:
        """Return current token position index for state capture."""

    @abstractmethod
    def reset(self, index: int) -> None:
        """Restore tokenizer state to previously marked position.

        index: Marker from mark() method
        """

    @abstractmethod
    def get_lines(self, line_numbers: List[int]) -> List[str]:
        """Retrieve source lines by line number.

        line_numbers: List of 1-based line numbers

        Returns:
            Corresponding source lines
        """

    # Optional but recommended for advanced parsing
    def get_last_non_whitespace_token(self) -> TokenInfo:
        """Return most recent non-whitespace token.

        The default implementation returns `self.diagnose()`,
        not guaranteeing it is not a whitespace token."""
        return self.diagnose()


# Edition 1
class Tokenizer(AbstractTokenizer):
    """Caching wrapper for the tokenize module.

    This is pretty tied to Python's syntax.
    """

    _tokens: List[TokenInfo]

    # TODO: path
    def __init__(
        self, tokengen: Iterator[TokenInfo], *, path: str = "",
        verbose_stream: Optional[TextIO] = None
    ):
        self._tokengen = tokengen
        self._tokens = []
        self._index = 0
        self._verbose = verbose_stream is not None
        self._lines: Dict[int, str] = {}
        self._path = path
        self._verbose_stream = verbose_stream
        if self._verbose:
            self.log(False, False)

    @classmethod
    def from_text(cls, text: str, *, path: str = "", verbose_stream: Optional[TextIO] = None) -> Self:
        stream = io.StringIO(text)
        instance = cls(tokenize.generate_tokens(stream.readline), path=path, verbose_stream=verbose_stream)
        finalize(instance, lambda: stream.close() if not stream.closed else None) #XXX: Should be ok?
        return instance

    @classmethod
    def from_tokens(cls, tokens: Iterator[TokenInfo], *, path: str = "", verbose_stream: Optional[TextIO] = None) -> Self:
        return cls(tokens, path=path, verbose_stream=verbose_stream)

    @classmethod
    def from_stream(cls, file: TextIO, *, path: str = "", verbose_stream: Optional[TextIO] = None) -> Self:
        return cls(tokenize.generate_tokens(file.readline), path=path, verbose_stream=verbose_stream)

    def getnext(self) -> TokenInfo:
        """Return the next token and updates the index."""
        cached = not self._index == len(self._tokens)
        tok = self.peek()
        self._index += 1
        if self._verbose:
            self.log(cached, False)
        return tok

    def peek(self) -> TokenInfo:
        """Return the next token *without* updating the index."""
        while self._index == len(self._tokens):
            tok = next(self._tokengen)
            if tok.type in (tokenize.NL, tokenize.COMMENT):
                continue
            if tok.type == token.ERRORTOKEN and tok.string.isspace():
                continue
            if (
                tok.type == token.NEWLINE
                and self._tokens
                and self._tokens[-1].type == token.NEWLINE
            ):
                continue
            self._tokens.append(tok)
            if not self._path and tok.start[0] not in self._lines:
                self._lines[tok.start[0]] = tok.line
        return self._tokens[self._index]

    def diagnose(self) -> TokenInfo:
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def get_last_non_whitespace_token(self) -> TokenInfo:
        for tok in reversed(self._tokens[: self._index]):
            if tok.type != tokenize.ENDMARKER and (
                tok.type < tokenize.NEWLINE or tok.type > tokenize.DEDENT
            ):
                break
        return tok #type:ignore

    def get_lines(self, line_numbers: List[int]) -> List[str]:
        """Retrieve source lines corresponding to line numbers."""
        if self._lines:
            lines = self._lines
        else:
            n = len(line_numbers)
            lines = {}
            count = 0
            seen = 0
            with open(self._path) as f: #?
                for line in f:
                    count += 1
                    if count in line_numbers:
                        seen += 1
                        lines[count] = line
                        if seen == n:
                            break

        return [lines[n] for n in line_numbers]

    def mark(self) -> Mark:
        return self._index

    def reset(self, index: Mark) -> None:
        if index == self._index:
            return
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        old_index = self._index
        self._index = index
        if self._verbose:
            self.log(True, index < old_index)

    def log(self, cached: bool, back: bool) -> None:
        if back:
            fill = "-" * self._index + "-"
        elif cached:
            fill = "-" * self._index + ">"
        else:
            fill = "-" * self._index + "*"
        if self._index == 0:
            print(f"{fill} (Bof)")
        else:
            tok = self._tokens[self._index - 1]
            print(f"{fill} {shorttok(tok)}")
