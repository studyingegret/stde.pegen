from dataclasses import dataclass
from typing import Generic, Type, TypeVar, TypeVarTuple, Union
from pegen.grammar import Grammar
from pegen.tokenizer import Tokenizer
from pegen.parser import Parser
from pegen.parser_v2 import BaseParser
from pegen.parser_generator import ParserGenerator

WithGrammar = Grammar
"""1st generic argument"""
WithGrammarParser = Parser
"""2nd generic argument"""
WithGrammarTokenizer = Tokenizer
"""3rd generic argument"""
WithParserCodeGenerator = ParserGenerator
"""4th generic argument"""
WithParserCode = str
"""5th generic argument"""
WithParserClass = Type[BaseParser]
"""6th generic argument"""

T1 = TypeVar("T1", WithGrammar, None, Union[WithGrammar, None], covariant=True)
T2 = TypeVar("T2", WithGrammarParser, None, Union[WithGrammarParser, None], covariant=True)
T3 = TypeVar("T3", WithGrammarTokenizer, None, Union[WithGrammarTokenizer, None], covariant=True)
T4 = TypeVar("T4", WithParserCodeGenerator, None, Union[WithParserCodeGenerator, None], covariant=True)
T5 = TypeVar("T5", WithParserCode, None, Union[WithParserCode, None], covariant=True)
T6 = TypeVar("T6", WithParserClass, None, Union[WithParserClass, None], covariant=True)
MoreTs = TypeVarTuple("MoreTs")

@dataclass(slots=True, frozen=True)
class BuiltProducts(Generic[T1, T2, T3, T4, T5, T6, *MoreTs]):
    """The built products.

    ## Generic notation for signaling "what will be generated"
    TODO
    ---

    `class_` is an alias for `parser_class`.
    """
    grammar: T1
    grammar_parser: T2
    grammar_tokenizer: T3
    parser_code_generator: T4
    parser_code: T5
    parser_class: T6

    @property
    def class_(self) -> T6:
        return self.parser_class