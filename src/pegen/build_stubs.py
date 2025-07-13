# This type stub is to make "what fields will be filled out" displayed in IDE type infos.
# It is ignored at runtime.
# See definition in module build for real implementation.

from dataclasses import dataclass
from typing import TYPE_CHECKING
assert TYPE_CHECKING

from typing import Generic, Optional, Type, TypeVar, Literal, Union
from pegen.grammar import Grammar
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.tokenizer import Tokenizer

Y = Literal[True]
N = Literal[False]
M = Union[Y, N]

# Whether each field is filled out is generic
HasGrammar = TypeVar("HasGrammar", Y, N, M, covariant=True)
HasGrammarParser = TypeVar("HasGrammarParser", Y, N, M, covariant=True)
HasGrammarTokenizer = TypeVar("HasGrammarTokenizer", Y, N, M, covariant=True)
HasParserCodeGenerator = TypeVar("HasParserCodeGenerator", Y, N, M, covariant=True)
HasParserCode = TypeVar("HasParserCode", Y, N, M, covariant=True)
HasParserClass = TypeVar("HasParserClass", Y, N, M, covariant=True)


@dataclass(slots=True)
class BuiltProducts(Generic[
    HasGrammar, HasGrammarParser, HasGrammarTokenizer, HasParserCodeGenerator, HasParserCode, HasParserClass
]):
    """TODO: Doc"""
    grammar: Optional[Grammar]
    grammar_parser: Optional[Parser]
    grammar_tokenizer: Optional[Tokenizer]
    parser_code_generator: Optional[ParserGenerator]
    parser_code: Optional[str]
    parser_class: Optional[Type[Parser]]

    @property
    def class_(self) -> Optional[Type[Parser]]: ...

