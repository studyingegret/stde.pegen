# This version is the same as build_types.py, the runtime version.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Tuple, Type, TypeVar, TypeVarTuple, Union, Unpack
from pegen.grammar import Grammar
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.tokenizer import Tokenizer

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
WithParserClass = Type[Parser]
"""6th generic argument"""

T1 = TypeVar("T1", WithGrammar, None, Union[WithGrammar, None], covariant=True)
T2 = TypeVar("T2", WithGrammarParser, None, Union[WithGrammarParser, None], covariant=True)
T3 = TypeVar("T3", WithGrammarTokenizer, None, Union[WithGrammarTokenizer, None], covariant=True)
T4 = TypeVar("T4", WithParserCodeGenerator, None, Union[WithParserCodeGenerator, None], covariant=True)
T5 = TypeVar("T5", WithParserCode, None, Union[WithParserCode, None], covariant=True)
T6 = TypeVar("T6", WithParserClass, None, Union[WithParserClass, None], covariant=True)
#MoreTs = TypeVarTuple("MoreTs", default=Unpack[Tuple[()]])
MoreTs = TypeVarTuple("MoreTs")

# mypy complains: "BuiltProducts" both defines "__slots__" and is used with "slots=True"
# though I can't see where I defined __slots__
#@dataclass(slots=True, frozen=True)
@dataclass(frozen=True)
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

    def __init__(self, grammar: T1, grammar_parser: T2, grammar_tokenizer: T3,
                 parser_code_generator: T4, parser_code: T5, parser_class: T6,
                 *args: *MoreTs):
        object.__setattr__(self, "grammar", grammar)
        object.__setattr__(self, "grammar_parser", grammar_parser)
        object.__setattr__(self, "grammar_tokenizer", grammar_tokenizer)
        object.__setattr__(self, "parser_code_generator", parser_code_generator)
        object.__setattr__(self, "parser_code", parser_code)
        object.__setattr__(self, "parser_class", parser_class)

    @property
    def class_(self) -> T6:
        return self.parser_class

# Test the display in mypy (not complete yet)
# NOTE: I haven't tested yet
if TYPE_CHECKING:
    from typing import cast

    def test_code() -> None:
        import random
        g = cast(Grammar, 0)  # grammar
        gp = cast(Parser, 0)  # grammar_parser
        gt = cast(Tokenizer, 0)  # grammar_tokenizer
        pcg = cast(ParserGenerator, 0)  # parser_code_generator
        pcode = "a"  # parser_code
        pcls = cast(Type[Parser], 0)  # parser_class

        def func() -> BuiltProducts[ #type:ignore[empty-body]
            Union[WithGrammar, None], Union[WithGrammarParser, None], WithGrammarTokenizer,
            WithParserCodeGenerator, WithParserCode, WithParserClass
        ]:
            """Return type name should remain as-is (or nearly as-is(?)) in signature hint"""
            ...

        test: BuiltProducts[
            Union[WithGrammar, None], Union[WithGrammarParser, None], WithGrammarTokenizer,
            WithParserCodeGenerator, WithParserCode, WithParserClass]
        #reveal_type(test)
        #reveal_type(BuiltProducts[
        #    Union[WithGrammar, None], Union[WithGrammarParser, None], WithGrammarTokenizer,
        #    WithParserCodeGenerator, WithParserCode, WithParserClass])

        # Statements should pass unless where noted in comments

        # Branch of union
        a = BuiltProducts(g, None, gt, pcg, pcode, pcls) #type:ignore[var-annotated]
        #reveal_type(a)
        test = a
        """Type of a in IDE (e.g. hover hint) should be shown as:
        BuiltProducts[WithGrammar, None, WithGrammarTokenizer,
        WithParserCodeGenerator, WithParserCode, WithParserClass, <extra content here is accepted>]
        """

        # Type should show "Tokenizer"
        a.grammar_tokenizer
        #reveal_type(a.grammar_tokenizer)

        # Full range of union
        b = BuiltProducts(random.choice([g, None]), random.choice([gp, None]), gt, pcg, pcode, pcls) #type:ignore[var-annotated]
        test = b
        """Type of b in IDE (e.g. hover hint) should be shown as:
        BuiltProducts[WithGrammar | None, WithGrammarParser | None, WithGrammarTokenizer,
        WithParserCodeGenerator, WithParserCode, WithParserClass, <extra content here is accepted>]
        """

        # Possible types too wide
        c = BuiltProducts(g, gp, random.choice([gt, None]), pcg, pcode, pcls)
        # Assignment should fail like 'Type "WithGrammarTokenizer | None" is not assignable to type "WithGrammarTokenizer"'
        # Uncomment this to test (remember to re-comment when committing :))
        #test = c
        """Type of c in IDE (e.g. hover hint) should be shown as:
        BuiltProducts[WithGrammar, WithGrammarParser, WithGrammarTokenizer | None,
        WithParserCodeGenerator, WithParserCode, WithParserClass, <extra content here is accepted>]
        """