#import pathlib
import tokenize, io
from typing import Dict, Set, Tuple, Optional, Type, Union, cast

from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.utils2 import open_file, File

#Unused
#MOD_DIR = pathlib.Path(__file__).resolve().parent

TokenDefinitions = Tuple[Dict[int, str], Dict[str, int], Set[str]]


# Note: Architecture limits we cannot directly generate grammar from a grammar string.


#...
def _grammar_file_name_or_fallback(grammar_file_name: Optional[str], grammar_file: File,
                                   fallback: str = "<unknown>") -> str:
    if grammar_file_name is not None:
        return grammar_file_name
    if isinstance(grammar_file, str):
        return grammar_file
    return str(grammar_file.name) if hasattr(grammar_file, "name") else "<unknown>" #type:ignore


def load_grammar(
    grammar_file: File, verbose_tokenizer: bool = False, verbose_parser: bool = False,
    *, grammar_file_name: Optional[str] = None
) -> Tuple[Grammar, Parser, Tokenizer]:
    """Build grammar from grammar_file.

    Returns a 3-tuple of
    - The built grammar (Grammar)
    - Middleware product GrammarParser
    - Middleware product Tokenizer
    """
    grammar_file_name = _grammar_file_name_or_fallback(grammar_file_name, grammar_file)
    with open_file(grammar_file) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        grammar = parser.start()

        if not grammar:
            raise parser.make_syntax_error("Cannot parse grammar file.", grammar_file_name)

    return grammar, parser, tokenizer


def load_grammar_from_string(
    grammar_string: str, verbose_tokenizer: bool = False, verbose_parser: bool = False,
    *, grammar_file_name: Optional[str] = None
) -> Tuple[Grammar, Parser, Tokenizer]:
    with io.StringIO(grammar_string) as tempfile:
        return load_grammar(tempfile, verbose_tokenizer, verbose_parser,
                            grammar_file_name=grammar_file_name)

def generate_code_from_grammar(
    grammar: Grammar,
    grammar_file_name: str, # Note: Used for noting source in generated header
    output_file: File,
    skip_actions: bool = False,
) -> ParserGenerator:
    """Generates Python parser code to output_file.

    Returns middleware product ParserGenerator.
    """
    print(grammar,grammar_file_name,output_file,skip_actions)
    with open_file(output_file, "w") as file:
        gen: ParserGenerator = PythonParserGenerator(grammar, file, skip_actions=skip_actions)
        gen.generate(grammar_file_name)
    return gen


def generate_code_from_file(
    grammar_file: File,
    output_file: File,
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
) -> Tuple[Grammar, Parser, Tokenizer, ParserGenerator]:
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
    grammar_file_name = _grammar_file_name_or_fallback(grammar_file_name, grammar_file)
    grammar, parser, tokenizer = load_grammar(grammar_file, verbose_tokenizer, verbose_parser)
    gen = generate_code_from_grammar(grammar, grammar_file_name, output_file, skip_actions=skip_actions)
    return grammar, parser, tokenizer, gen


def generate_parser_from_grammar(
    grammar: Union[str, Grammar],
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
    parser_class_name: str = "GeneratedParser",
) -> Tuple[Optional[Grammar], Optional[Parser], Optional[Tokenizer], ParserGenerator, Type[Parser]]:
    """[TODO]
    verbose_tokenizer, verbose_parser and grammar_file_name are only effective when grammar is a str.
    """
    if grammar_file_name is None:
        grammar_file_name =" <generate_parser_from_grammar>"
    # Grammar string → Grammar
    ret_grammar = parser = tokenizer = None
    if isinstance(grammar, str):
        grammar, parser, tokenizer = load_grammar_from_string(
            grammar, verbose_tokenizer, verbose_parser, grammar_file_name=grammar_file_name)
        ret_grammar = grammar
    grammar = cast(Grammar, grammar)  # Type checkers
    # Grammar → Parser code
    with io.StringIO() as fout:
        gen = generate_code_from_grammar(grammar, grammar_file_name, fout, skip_actions)
        code = fout.getvalue()
    # Parser code → Parser class
    ns = {}
    exec(code, ns)
    return ret_grammar, parser, tokenizer, gen, ns[parser_class_name]


def generate_parser_from_file(
    grammar_file: File,
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
    *,
    grammar_file_name: Optional[str] = None,
    parser_class_name: str = "GeneratedParser",
) -> Tuple[Grammar, Parser, Tokenizer, ParserGenerator, Type[Parser]]:
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
    grammar, parser, tokenizer = load_grammar(
        grammar_file, verbose_tokenizer, verbose_parser, grammar_file_name=grammar_file_name)
    # Grammar → Parser class
    _1, _2, _3, gen, parser_class = generate_parser_from_grammar(
        grammar, verbose_tokenizer, verbose_parser, skip_actions,
        grammar_file_name=grammar_file_name, parser_class_name=parser_class_name
    )
    return grammar, parser, tokenizer, gen, parser_class