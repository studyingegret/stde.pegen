import pathlib
import tokenize
from typing import Dict, Set, Tuple, Optional

from pegen.grammar import Grammar
from pegen.grammar_parser import GeneratedParser as GrammarParser
from pegen.parser import Parser
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import PythonParserGenerator
from pegen.tokenizer import Tokenizer
from pegen.utils2 import open_file, File

MOD_DIR = pathlib.Path(__file__).resolve().parent

TokenDefinitions = Tuple[Dict[int, str], Dict[str, int], Set[str]]


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
    with open_file(grammar_file) as file:
        tokenizer = Tokenizer(tokenize.generate_tokens(file.readline), verbose=verbose_tokenizer)
        parser = GrammarParser(tokenizer, verbose=verbose_parser)
        grammar = parser.start()

        if not grammar:
            if grammar_file_name is None:
                if hasattr(grammar_file, "name"):
                    grammar_file_name = str(grammar_file.name) #type:ignore
                else:
                    grammar_file_name = "<unknown>"
            raise parser.make_syntax_error("Cannot parse grammar file.", grammar_file_name)

    return grammar, parser, tokenizer


def generate_parser_from_grammar(
    grammar: Grammar,
    grammar_file: File,
    output_file: File,
    skip_actions: bool = False,
) -> ParserGenerator:
    """Generates Python parser code to output_file.

    Returns middleware product ParserGenerator.
    """
    with open_file(output_file, "w") as file:
        gen: ParserGenerator = PythonParserGenerator(grammar, file, skip_actions=skip_actions)
        gen.generate(grammar_file)
    return gen


def generate_parser_from_file(
    grammar_file: str, #TODO: Accept IO | None
    output_file: str, #TODO: Accept IO | None
    verbose_tokenizer: bool = False,
    verbose_parser: bool = False,
    skip_actions: bool = False,
) -> Tuple[Grammar, Parser, Tokenizer, ParserGenerator]:
    """Loads grammar from grammar_file and generates Python parser code to output_file.

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
    grammar, parser, tokenizer = load_grammar(grammar_file, verbose_tokenizer, verbose_parser)
    gen = generate_parser_from_grammar(
        grammar,
        grammar_file,
        output_file,
        skip_actions=skip_actions,
    )
    return grammar, parser, tokenizer, gen
