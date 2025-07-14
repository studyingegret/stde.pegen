# This type stub is to make "what fields will be filled out" displayed in IDE type infos.
# It is ignored at runtime.
# See definition in module build for real implementation.
#
# Test code of stubs is present at end of file (requires manual checking (probably)).

# XXX: Is this all overcomplicated?
# But I think it is useful for users to know
# what fields in a BuiltProducts are (statically known to be)
# really filled out, by just looking at signature,
# without reading functions' docstrings (they'll forget).

# TODO: Doc?

from typing import TYPE_CHECKING, Generic, TypeAlias, cast
assert TYPE_CHECKING, "Should never be imported at runtime"
from typing import Literal, Type, TypeVar, TypeVarTuple, Union
from pegen.grammar import Grammar
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.tokenizer import Tokenizer

__all__ = ["WithGrammar", "WithGrammarParser", "WithGrammarTokenizer",
           "WithParserCodeGenerator", "WithParserCode", "WithParserClass"]

# Union with Literal[x] to make the new type complex enough
# so that IDEs won't expand it.
# The case Literal[x] is then asserted false in __init__.
#
# The only caveats are that
# - Code could write Grammar instead of WithGrammar (etc.)
#   as a generic parameter. But I personally think the problem is not serious.
# - BuildProduct fields' type display may be strange(?) but I can only
#   fix them on a best-effort basis.
#   Their display is acceptable in Pylance.
#
# Test code of stubs is present at end of file (requires manual checking (probably)).
WithGrammar: TypeAlias = Union[Literal[0], Grammar]
"""1st generic argument"""
WithGrammarParser: TypeAlias = Union[Literal[0], Parser]
"""2nd generic argument"""
WithGrammarTokenizer: TypeAlias = Union[Literal[0], Tokenizer]
"""3rd generic argument"""
WithParserCodeGenerator: TypeAlias = Union[Literal[0], ParserGenerator]
"""4th generic argument"""
WithParserCode: TypeAlias = Union[Literal[0], str]
"""5th generic argument"""
WithParserClass: TypeAlias = Union[Literal[0], Type[Parser]]
"""6th generic argument"""
T1 = TypeVar("T1", WithGrammar, None, Union[WithGrammar, None], covariant=True)
T2 = TypeVar("T2", WithGrammarParser, None, Union[WithGrammarParser, None], covariant=True)
T3 = TypeVar("T3", WithGrammarTokenizer, None, Union[WithGrammarTokenizer, None], covariant=True)
T4 = TypeVar("T4", WithParserCodeGenerator, None, Union[WithParserCodeGenerator, None], covariant=True)
T5 = TypeVar("T5", WithParserCode, None, Union[WithParserCode, None], covariant=True)
T6 = TypeVar("T6", WithParserClass, None, Union[WithParserClass, None], covariant=True)
MoreTs = TypeVarTuple("MoreTs") # Future compatibility

class BuiltProducts(Generic[T1, T2, T3, T4, T5, T6, *MoreTs]):
    # This definition is a type stub only.
    # Real definition is in build.py.

    def __init__(self, grammar: T1, grammar_parser: T2, grammar_tokenizer: T3,
                 parser_code_generator: T4, parser_code: T5, parser_class: T6):
        assert grammar != 0
        assert grammar_parser != 0
        assert grammar_tokenizer != 0
        assert parser_code_generator != 0
        assert parser_code != 0
        assert parser_class != 0
        self.grammar = grammar #...
        self.grammar_parser = grammar_parser #...
        self.grammar_tokenizer = grammar_tokenizer #...
        self.parser_code_generator = parser_code_generator #...
        self.parser_code = parser_code #...
        self.parser_class = parser_class #...

    @property
    def class_(self):  #type:ignore
        return self.parser_class

#class BuiltProducts(_BuiltProducts[T1, T2, T3, T4, T5, T6, *MoreTs]):
#    def __init__(self, grammar: T1, grammar_parser: T2, grammar_tokenizer: T3,
#                 parser_code_generator: T4, parser_code: T5, parser_class: T6):
#        super().__init__(grammar,grammar_parser,grammar_tokenizer,parser_code_generator,parser_code,parser_class)
#        assert not isinstance(self.grammar_tokenizer, __I3)
#        self.grammar_tokenizer


# Test the display in IDEs (not complete yet)
if TYPE_CHECKING:
    import random
    g = cast(Grammar, 0)  # grammar
    gp = cast(Parser, 0)  # grammar_parser
    gt = cast(Tokenizer, 0)  # grammar_tokenizer
    pcg = cast(ParserGenerator, 0)  # parser_code_generator
    pcode = "a"  # parser_code
    pcls = cast(Type[Parser], 0)  # parser_class

    def func() -> BuiltProducts[
        Union[WithGrammar, None], Union[WithGrammarParser, None], WithGrammarTokenizer,
        WithParserCodeGenerator, WithParserCode, WithParserClass
    ]:
        """Return type name should remain as-is (or nearly as-is(?)) in signature hint"""
        ...

    test: BuiltProducts[
        Union[WithGrammar, None], Union[WithGrammarParser, None], WithGrammarTokenizer,
        WithParserCodeGenerator, WithParserCode, WithParserClass]

    # Statements should pass unless where noted in comments

    # Branch of union
    a = BuiltProducts(g, None, gt, pcg, pcode, pcls)
    test = a
    """Type of a in IDE (e.g. hover hint) should be shown as:
    BuiltProducts[WithGrammar, None, WithGrammarTokenizer,
    WithParserCodeGenerator, WithParserCode, WithParserClass, <extra content here is accepted>]
    """

    # Type should show "Tokenizer"
    a.grammar_tokenizer
    # Currently shows "Tokenizer*" in Pylance but is acceptable
    # https://github.com/microsoft/pylance-release/discussions/1707
    # https://github.com/microsoft/pyright/blob/046eab4a8dd8344ae614f9214f0871db64085163/docs/type-concepts.md#constrained-type-variables-and-conditional-types

    #reveal_type(a.grammar_tokenizer)

    # Full range of union
    b = BuiltProducts(random.choice([g, None]), random.choice([gp, None]), gt, pcg, pcode, pcls)
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
    """Type of b in IDE (e.g. hover hint) should be shown as:
    BuiltProducts[WithGrammar, WithGrammarParser, WithGrammarTokenizer | None,
    WithParserCodeGenerator, WithParserCode, WithParserClass, <extra content here is accepted>]
    """