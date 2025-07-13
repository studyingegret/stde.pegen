"""Build pegen products from sources.

    load_grammar_from_string: Grammar string → Grammar
    load_grammar_from_file: Grammar file → Grammar

    generate_code_from_grammar: Grammar → Generated parser code (str)
    generate_code_from_file: Grammar file → Generated parser code (str)

    generate_parser_from_grammar: Grammar or grammar string → Ready-to-use pegen.parser.Parser subclass
    generate_parser_from_file: Grammar file → Ready-to-use pegen.parser.Parser subclass

In the above description:
- "Grammar" means a pegen.grammar.Grammar instance
- "Grammar file" means a utils2.File compatible object
  (str, bytes, path-like (has method `__fspath__(self) -> Union[str, bytes]`), or text I/O object)

Note that generate_code_from_grammar does not accept grammar string,
you need to use load_grammar_from_string for grammar strings first.
However, generate_parser_from_grammar accepts grammar string.

## Migration from early versions
The old functions are still there but new code is encouraged to
use the new equivalents:
- build_parser → load_grammar_from_file
- build_python_generator → generate_code_from_grammar
- build_python_parser_and_generator → generate_code_from_file
"""

#TODO: Organize comments & docs

import tokenize, io
from dataclasses import dataclass
from enum import IntEnum
from typing import (TYPE_CHECKING, Literal, Never, Optional, Type, Union, cast)

from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.utils2 import open_file, File


# The purpose of the type stubs of BuiltProducts below:
# to make "what fields will be filled out" displayed in IDE type infos.
#
# For example, by seeing type hint
#   def load_grammar_from_file(...) -> BuiltProducts[Y, Y, Y, M, N, N]
# you know for BuiltProducts returned by load_grammar_from_file,
# grammar, grammar_parser, grammar_tokenizer will be filled out (will not be None),
# parser_code_generator might be filled out (might be None)
# parser_code, parser_class will not be filled out (will be None).
#
# Note: Writing BuiltProducts without generic notation is ok (?)

Y = Never  # Field will be filled out
N = Literal[None]  # Field will not be filled out
M = Union[Y, N]  # Field might be filled out

if TYPE_CHECKING:
    # To make IDEs display hints
    from build_stubs import BuiltProducts
else:
    # Real implementation
    @dataclass(slots=True, frozen=True)
    class BuiltProducts:
        """The built products.

        ## Generic notation for signaling "what will be generated"
        BuiltProducts can be written with six generics, each being `Y`, `N` or `M`;
        e.g. the return type of `load_grammar_from_file`:

            BuiltProducts[Y, Y, Y, M, N, N]

        It means
        - The first three fields (`grammar, grammar_parser, grammar_tokenizer`)
          will be generated, so they will not be None (`Y, Y, Y`).
        - The fourth field (`grammar_tokenizer`)
          might be generated, depending on arguments, so might be None (`M`).
        - The last two fields (`parser_code, parser_class`)
          will not be generated and will be None (`N, N`).

        This type feature helps you figure out what products to expect from
        a function by just looking at its signature.

        BuiltProducts can be written without generics.

        Note: Fields in order:
        `grammar, grammar_parser, grammar_tokenizer, parser_code_generator, parser_code, parser_class`

        ---

        `class_` is an alias for `parser_class`.
        """
        grammar: Optional[Grammar]
        grammar_parser: Optional[Parser]
        grammar_tokenizer: Optional[Tokenizer]
        parser_code_generator: Optional[ParserGenerator]
        parser_code: Optional[str]
        parser_class: Optional[Type[Parser]]

        @property
        def class_(self) -> Optional[Type[Parser]]:
            return self.parser_class

        def __class_getitem__(cls, x):
            return cls

class Return: pass

# Flag to set for parameter output_file
# in generate_code_from_grammar and generate_code_from_file:
# Tells to return code string (as tuple item) instead of generating it to output_file.
RETURN = Return()

DEFAULT_SOURCE_NAME_FALLBACK = "<unknown>"


def _grammar_file_name_fallback(
    grammar_file_name: Optional[str], grammar_file: File, fallback: str = DEFAULT_SOURCE_NAME_FALLBACK
) -> str:
    """Should only be used in _from_file functions.
    See also note in load_grammar_from_string.
    """
    if grammar_file_name is not None:
        return grammar_file_name
    # Is `grammar_file` a file name?
    if isinstance(grammar_file, (str, bytes)):
        return str(grammar_file)  # We give up decoding bytes
    # Weak duck-checking of os.PathLike/utils2.PathLike
    # (really because I'm reluctant to add runtime_checkable for utils2.PathLike)
    if hasattr(grammar_file, "__fspath__") and callable(grammar_file.__fspath__):  #type:ignore
        #XXX: Should catch exception here?
        p = grammar_file.__fspath__()  #type:ignore
        if isinstance(p, (str, bytes)):
            return str(p)  # We give up decoding bytes
    # Files returned by open() have a name attribute
    if hasattr(grammar_file, "name"):
        return str(grammar_file.name)  #type:ignore
    return fallback


def load_grammar_from_file(
    grammar_file: File, verbose_tokenizer: bool = False, verbose_parser: bool = False,
    *, grammar_file_name: Optional[str] = None
) -> BuiltProducts[Y, Y, Y, N, N, N]:
    """Returns BuiltProducts with fields grammar, parser and tokenizer filled."""
    grammar_file_name = _grammar_file_name_fallback(grammar_file_name, grammar_file)
    with open_file(grammar_file) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        grammar = parser.start()
        if not grammar:
            raise parser.make_syntax_error("Cannot parse grammar file.", grammar_file_name)
    return BuiltProducts(grammar, parser, tokenizer, None, None, None)


# Architecture limits we cannot directly generate grammar from a grammar string.
def load_grammar_from_string(
    grammar_string: str, verbose_tokenizer: bool = False, verbose_parser: bool = False,
    *, grammar_file_name: Optional[str] = None
) -> BuiltProducts[Y, Y, Y, N, N, N]:
    """Returns BuiltProducts with fields grammar, parser and tokenizer filled."""
    # Note:
    # If a source name of the grammar string (where it comes from)
    # is not given (grammar_file_name is None), use function name as source.
    # This applies to _from_string/_from_grammar functions,
    # and is different from _from_file functions.
    if grammar_file_name is None:
        grammar_file_name = "<load_grammar_from_string>"
    with io.StringIO(grammar_string) as tempfile:
        return load_grammar_from_file(
            tempfile, verbose_tokenizer, verbose_parser,
            grammar_file_name=grammar_file_name)


# Note: grammar_file_name is used for noting source in generated header
def generate_code_from_grammar(
    grammar: Grammar,
    grammar_file_name: Optional[str] = None,
    output_file: Union[File, Return] = RETURN,
    skip_actions: bool = False,
) -> BuiltProducts[N, N, N, Y, M, N]:
    """[TODO] Generates Python parser code to output_file.

    Returns middleware product ParserGenerator.
    """
    if grammar_file_name is None:
        grammar_file_name = "<generate_code_from_grammar>"
    if output_file is RETURN:
        with io.StringIO() as file:
            gen = PythonParserGenerator(grammar, file, skip_actions=skip_actions)
            gen.generate(grammar_file_name)
            return BuiltProducts(None, None, None, gen, file.getvalue(), None)
    else:
        if TYPE_CHECKING: output_file = cast(File, output_file)
        with open_file(output_file, "w") as file:
            gen = PythonParserGenerator(grammar, file, skip_actions=skip_actions)
            gen.generate(grammar_file_name)
            return BuiltProducts(None, None, None, gen, None, None)


def generate_code_from_file(
    grammar_file: File,
    output_file: Union[File, Return] = RETURN,
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
) -> BuiltProducts[Y, Y, Y, Y, M, N]:
    """Output Python parser code to output_file from grammar in grammar_file.

    Args: [TODO]
        grammar_file: Path or io.StringIO of the grammar file
        output_file: Path or io.StringIO for the output file
        verbose_tokenizer: Whether to display additional output when generating the tokenizer.
          Defaults to False.
        verbose_parser: Whether to display additional output when generating the parser.
          Defaults to False.
        skip_actions: Whether to pretend actions are not there. Default actions will be generated.
          Defaults to False.

    Returns:
    - The loaded grammar (Grammar)
    - Middleware byproduct GrammarParser
    - Middleware byproduct Tokenizer
    - Middleware byproduct ParserGenerator
    """
    grammar_file_name = _grammar_file_name_fallback(grammar_file_name, grammar_file)
    p = load_grammar_from_file(grammar_file, verbose_tokenizer, verbose_parser)
    p2 = generate_code_from_grammar(p.grammar, grammar_file_name, output_file, skip_actions=skip_actions)
    return BuiltProducts(p.grammar, p.grammar_parser, p.grammar_tokenizer,
                         p2.parser_code_generator, p2.parser_code, None)


def generate_parser_from_grammar(
    grammar: Union[str, Grammar],
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
    parser_class_name: str = "GeneratedParser",
) -> BuiltProducts[M, M, M, Y, N, Y]:
    """[TODO]
    verbose_tokenizer, verbose_parser and grammar_file_name are only effective when grammar is a str.
    """
    if grammar_file_name is None:
        grammar_file_name = "<generate_parser_from_grammar>"
    # Grammar string → Grammar
    generated_grammar = None  # None if didn't actually generate
    if isinstance(grammar, str):
        p = load_grammar_from_string(grammar, verbose_tokenizer, verbose_parser,
                                     grammar_file_name=grammar_file_name)
        generated_grammar = grammar = p.grammar
    # Grammar → Parser code
    p2 = generate_code_from_grammar(grammar, grammar_file_name, RETURN, skip_actions)
    # Parser code → Parser class
    ns = {}
    exec(cast(str, p2.parser_code), ns)
    return BuiltProducts(generated_grammar, p.grammar_parser, p.grammar_tokenizer,
                         p2.parser_code_generator, None, ns[parser_class_name])


def generate_parser_from_file(
    grammar_file: File,
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
    parser_class_name: str = "GeneratedParser",
#) -> Tuple[Grammar, Parser, Tokenizer, ParserGenerator, Type[Parser]]:
) -> BuiltProducts[Y, Y, Y, Y, N, Y]:
    """[TODO] Generates a Python parser class from grammar in grammar_file.

    Args: Same as generate_code_from_file except that output_file is removed and
        parser_class_name is the name of the generated parser class
        (default "GeneratedParser"; could be changed with @class meta).

    Returns:
    - The loaded grammar (Grammar)
    - Middleware byproduct GrammarParser
    - Middleware byproduct Tokenizer
    - Middleware byproduct ParserGenerator
    - The generated parser (Type[Parser])
    """
    # Grammar file → Grammar
    p = load_grammar_from_file(
        grammar_file, verbose_tokenizer, verbose_parser, grammar_file_name=grammar_file_name)
    # Grammar → Parser class
    p2 = generate_parser_from_grammar(
        p.grammar, verbose_tokenizer, verbose_parser, skip_actions,
        grammar_file_name=grammar_file_name, parser_class_name=parser_class_name
    )
    return BuiltProducts(p.grammar, p.grammar_parser, p.grammar_tokenizer,
                         p2.parser_code_generator, None, p2.parser_class)

# TODO: Legacy

"""
def build_parser(
    grammar_file: str, verbose_tokenizer: bool = False, verbose_parser: bool = False
) -> Tuple[Grammar, Parser, Tokenizer]

def build_python_generator(
    grammar: Grammar,
    grammar_file: str,
    output_file: str,
    skip_actions: bool = False,
) -> ParserGenerator

def build_python_parser_and_generator(
    grammar_file: str,
    output_file: str,
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
) -> Tuple[Grammar, Parser, Tokenizer, ParserGenerator]
"""