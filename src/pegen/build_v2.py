"""[TODO]
Build pegen products from sources.

    load_grammar_from_string: Grammar string → Grammar
    load_grammar_from_file: Grammar file → Grammar

    generate_code_from_grammar: Grammar → Generated parser code (str)
    generate_code_from_file: Grammar file → Generated parser code (str)

    generate_parser_from_code: Generated parser code (str) → Ready-to-use pegen.parser_v2.BaseParser subclass
    generate_parser_from_grammar: Grammar or grammar string → Ready-to-use pegen.parser_v2.BaseParser subclass
    generate_parser_from_file: Grammar file → Ready-to-use pegen.parser_v2.BaseParser subclass

In the above description:
- "Grammar" means a pegen.grammar.Grammar instance
- "Grammar file" means a utils2.File compatible object
  (str, bytes, path-like (has method `__fspath__(self) -> Union[str, bytes]`), or text I/O object)

WARNING: generate_parser_from_code evaluates Python code using exec()
so do not pass it parser code from untrusted sources.

Note that generate_code_from_grammar does not accept grammar string,
you need to use load_grammar_from_string for grammar strings first.
However, generate_parser_from_grammar accepts grammar string.

## Migration from early versions
The old functions are still there but new code is encouraged to
use the new equivalents because the legacy functions are not tested anymore:
- build_parser → load_grammar_from_file
- build_python_generator → generate_code_from_grammar
- build_python_parser_and_generator → generate_code_from_file
"""

#TODO: Organize comments & docs

from enum import Enum
from functools import partial
import sys
import tokenize, io
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, Optional, TextIO, Tuple, Type, Union, Protocol, cast

from pegen.common import DEFAULT_PARSER_CLASS_NAME
from pegen.grammar_v2 import Grammar
#from pegen.parser import Parser
from pegen.parser_v2 import FAILURE, BaseParser
from pegen.tokenizer import Tokenizer
#from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from pegen.parser_generator_v2 import ParserGenerator
from pegen.python_generator_v2 import PythonParserGenerator
from pegen.utils2 import open_file, File

__all__ = ["Grammar", "BaseParser", "Tokenizer", "GrammarParser", "ParserGenerator",
           "PythonParserGenerator", "Flags",
           "load_grammar_from_string", "load_grammar_from_file",
           "generate_code_from_grammar", "generate_code_from_file",
           "generate_parser_from_grammar", "generate_parser_from_file",
           ]


# To make it usable in Literal, I make it an enum
# Hopefully it's not so disturbing
class Flags(Enum):
    RETURN = 0
    """Flag to set for parameter `output_file`
    in `generate_code_from_grammar` and `generate_code_from_file`:
    Return code string (as tuple item) instead of generating it to output_file."""


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
    if hasattr(grammar_file, "__fspath__") and callable(grammar_file.__fspath__): #pyright:ignore
        #XXX: Should catch exception here?
        p = grammar_file.__fspath__() #pyright:ignore
        if isinstance(p, (str, bytes)):
            return str(p)  # We give up decoding bytes
    # Files returned by open() have a name attribute
    if hasattr(grammar_file, "name"):
        return str(grammar_file.name) #pyright:ignore
    return fallback


"""
The basic functions are load_grammar_from_file, load_grammar_from_string,
generate_code_from_grammar and generate_parser_from_code.
All other functions are their combinations.

flowchart TD
file --> grammar
string -->|StringIO| file
grammar --> code
code --> parser
"""

class GrammarFromFileProducts(NamedTuple):
    grammar: Grammar
    grammar_parser: BaseParser
    grammar_tokenizer: Tokenizer

def load_grammar_from_file(
    grammar_file: File,
    tokenizer_verbose_stream: Optional[TextIO] = None,
    parser_verbose_stream: Optional[TextIO] = None,
    *, grammar_file_name: Optional[str] = None
) -> GrammarFromFileProducts:
    """Returns BuiltProducts with fields grammar, parser and tokenizer filled."""
    grammar_file_name = _grammar_file_name_fallback(grammar_file_name, grammar_file)
    with open_file(grammar_file) as file:
        tokenizer = Tokenizer.from_stream(file, verbose_stream=tokenizer_verbose_stream)
        parser = GrammarParser(tokenizer, verbose_stream=parser_verbose_stream)
        #grammar = parser.start()
        #if not grammar:
        #    raise parser.make_syntax_error("Can't parse grammar file.", grammar_file_name)
        grammar = parser.start()
        if grammar is FAILURE:
            raise parser.make_syntax_error("Can't parse grammar file.", grammar_file_name)
    return GrammarFromFileProducts(grammar, parser, tokenizer)


class GrammarFromStringProducts(NamedTuple):
    grammar: Grammar
    grammar_parser: BaseParser
    grammar_tokenizer: Tokenizer

def load_grammar_from_string(
    grammar_string: str,
    tokenizer_verbose_stream: Optional[TextIO] = None,
    parser_verbose_stream: Optional[TextIO] = None,
    *, grammar_file_name: Optional[str] = None
) -> GrammarFromStringProducts:
    """Returns BuiltProducts with fields grammar, parser and tokenizer filled."""
    # Note:
    # If a source name of the grammar string (where it comes from)
    # is not given (grammar_file_name is None), use function name as source.
    # This applies to _from_string/_from_grammar functions,
    # and is different from _from_file functions.
    if grammar_file_name is None:
        grammar_file_name = "<load_grammar_from_string>"
    tokenizer = Tokenizer.from_text(grammar_string, verbose_stream=tokenizer_verbose_stream)
    parser = GrammarParser(tokenizer, verbose_stream=parser_verbose_stream)
    grammar = parser.start()
    if grammar is FAILURE:
        raise parser.make_syntax_error("Can't parse grammar file.", grammar_file_name)
    return GrammarFromStringProducts(grammar, parser, tokenizer)


class CodeFromGrammarProducts(NamedTuple):
    parser_code_generator: ParserGenerator
    parser_code: Optional[str]

# Note: grammar_file_name is used for noting source in generated header
def generate_code_from_grammar(
    grammar: Grammar,
    grammar_file_name: Optional[str] = None,
    output_file: Union[File, Literal[Flags.RETURN]] = Flags.RETURN,
    skip_actions: bool = False,
) -> CodeFromGrammarProducts:
    if grammar_file_name is None:
        grammar_file_name = "<generate_code_from_grammar>"
    gen = PythonParserGenerator(grammar, skip_actions=skip_actions)
    if output_file is Flags.RETURN:
        with io.StringIO() as file:
            gen.generate(file, grammar_file_name)
            return CodeFromGrammarProducts(gen, file.getvalue())
    else:
        with open_file(output_file, "w") as file:
            gen = PythonParserGenerator(grammar, skip_actions=skip_actions)
            gen.generate(file, grammar_file_name)
            return CodeFromGrammarProducts(gen, None)


class ParserFromCodeProducts(NamedTuple):
    parser_class: Type[BaseParser]

def generate_parser_from_code(parser_code: str, parser_class_name: str = "GeneratedParser",) -> ParserFromCodeProducts:
    """Warning: generate_parser_from_code evaluates Python code using exec()
    so do not pass it parser code from untrusted sources."""
    ns: Any = {}
    exec(parser_code, ns)
    return ParserFromCodeProducts(ns[parser_class_name])


class CodeFromFileProducts(NamedTuple):
    grammar: Grammar
    grammar_parser: BaseParser
    grammar_tokenizer: Tokenizer
    parser_code_generator: ParserGenerator
    parser_code: Optional[str]

def generate_code_from_file(
    grammar_file: File,
    output_file: Union[File, Literal[Flags.RETURN]] = Flags.RETURN,
    tokenizer_verbose_stream: Optional[TextIO] = None,
    parser_verbose_stream: Optional[TextIO] = None,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
) -> CodeFromFileProducts:
    grammar_file_name = _grammar_file_name_fallback(grammar_file_name, grammar_file)
    p = load_grammar_from_file(grammar_file, tokenizer_verbose_stream, parser_verbose_stream)
    p2 = generate_code_from_grammar(p.grammar, grammar_file_name, output_file,
                                    skip_actions=skip_actions)
    return CodeFromFileProducts(p.grammar, p.grammar_parser, p.grammar_tokenizer,
                                p2.parser_code_generator, p2.parser_code)


class ParserFromGrammarProducts(NamedTuple):
    grammar: Optional[Grammar]
    grammar_parser: Optional[BaseParser]
    grammar_tokenizer: Optional[Tokenizer]
    parser_code_generator: ParserGenerator
    parser_code: str
    parser_class: Type[BaseParser]

class _NullProducts1(NamedTuple):
    grammar: None = None
    grammar_parser: None = None
    grammar_tokenizer: None = None

def generate_parser_from_grammar(
    grammar: Union[str, Grammar],
    tokenizer_verbose_stream: Optional[TextIO] = None,
    parser_verbose_stream: Optional[TextIO] = None,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
) -> ParserFromGrammarProducts:
    """[TODO]
    tokenizer_verbose_stream, verbose_parser and grammar_file_name are only effective when grammar is a str.
    """
    if grammar_file_name is None:
        grammar_file_name = "<generate_parser_from_grammar>"
    # Grammar string → Grammar
    generated_grammar = None
    p: Union[GrammarFromStringProducts, _NullProducts1]
    if isinstance(grammar, str):
        p = load_grammar_from_string(grammar, tokenizer_verbose_stream, parser_verbose_stream,
                                     grammar_file_name=grammar_file_name)
        generated_grammar = grammar = p.grammar
    else:
        p = _NullProducts1()
    parser_class_name = grammar.metas.get("class", DEFAULT_PARSER_CLASS_NAME)
    # Grammar → Parser code
    p2 = generate_code_from_grammar(grammar, grammar_file_name, Flags.RETURN, skip_actions)
    if TYPE_CHECKING: assert p2.parser_code is not None # mypy knows this but Pylance doesn't
    # Parser code → Parser class
    return ParserFromGrammarProducts(
        generated_grammar, p.grammar_parser, p.grammar_tokenizer, p2.parser_code_generator,
        p2.parser_code, generate_parser_from_code(p2.parser_code, parser_class_name).parser_class)


class ParserFromFileProducts(NamedTuple):
    grammar: Grammar
    grammar_parser: BaseParser
    grammar_tokenizer: Tokenizer
    parser_code_generator: ParserGenerator
    parser_class: Type[BaseParser]

def generate_parser_from_file(
    grammar_file: File,
    tokenizer_verbose_stream: Optional[TextIO] = None,
    parser_verbose_stream: Optional[TextIO] = None,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None
) -> ParserFromFileProducts:
    # Grammar file → Grammar
    p = load_grammar_from_file(
        grammar_file, tokenizer_verbose_stream, parser_verbose_stream, grammar_file_name=grammar_file_name)
    # Grammar → Parser class
    p2 = generate_parser_from_grammar(
        p.grammar, tokenizer_verbose_stream, parser_verbose_stream, skip_actions,
        grammar_file_name=grammar_file_name)
    return ParserFromFileProducts(p.grammar, p.grammar_parser, p.grammar_tokenizer,
                                     p2.parser_code_generator, p2.parser_class)

