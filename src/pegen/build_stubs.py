# This type stub is to make "what fields will be filled out" displayed in IDE type infos.
# It is ignored at runtime.
# See definition in module build for real implementation.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Never
assert TYPE_CHECKING

from typing import Generic, Optional, Type, TypeVar, Literal, Union
from pegen.grammar import Grammar
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.tokenizer import Tokenizer

# These three are copied in module build
Y = Never  # Field will be filled out
N = Literal[None]  # Field will not be filled out
M = Union[Y, N]  # Field might be filled out

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
    grammar: Union[Grammar, HasGrammar]
    grammar_parser: Union[Parser, HasGrammarParser]
    grammar_tokenizer: Union[Tokenizer, HasGrammarTokenizer]
    parser_code_generator: Union[ParserGenerator, HasParserCodeGenerator]
    parser_code: Union[str, HasParserCode]
    parser_class: Union[Type[Parser], HasParserClass]

    @property
    def class_(self) -> Union[Type[Parser], HasParserClass]: ...

