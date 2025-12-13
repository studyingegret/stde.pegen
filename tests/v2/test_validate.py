from textwrap import dedent
import pytest
from stde.pegen.v2.parser import ParseFailure
from stde.pegen.v2.parser_generator import ParserGenerator
from stde.pegen.v2.grammar import Grammar
from stde.pegen.v2.build import load_grammar_from_string
from stde.pegen.v2.grammar_parser import GeneratedParser as GrammarParser
from stde.pegen.common import ValidationError


def load_grammar(grammar: str) -> Grammar:
    return load_grammar_from_string(dedent(grammar)).grammar


def test_needs_trailer_or_start() -> None:
    grammar = load_grammar("""
    a: a
    """)
    with pytest.raises(ValidationError,
        match="Grammar without a trailer must have a 'start' rule"):
        ParserGenerator.validate(grammar, set())

    grammar = load_grammar("""
    @trailer ""
    a: a
    """)
    ParserGenerator.validate(grammar, set())

    grammar = load_grammar("""
    start: start
    """)
    ParserGenerator.validate(grammar, set())


def test_no_leading_underscores() -> None:
    grammar = load_grammar("""
    _a: "a"
    start: _a
    """)
    with pytest.raises(ValidationError,
        match="Rule _a: Name cannot start with underscore"):
        ParserGenerator.validate(grammar, set())

    grammar = load_grammar("""
    start: _a
    extern _a
    """)
    with pytest.raises(ValidationError,
        match="Extern declaration _a: Name cannot start with underscore"):
        ParserGenerator.validate(grammar, set())

    grammar = load_grammar("""
    start: _a=NAME { "(Invalid even if _a is unused)" }
    """)
    with pytest.raises(ValidationError,
        match="In rule start: capture variable '_a': Name cannot start with underscore"):
        ParserGenerator.validate(grammar, set())


def test_all_names_must_be_known() -> None:
    grammar = load_grammar("""
    start: unknown_name
    """)
    with pytest.raises(ValidationError,
        match="In rule start: 'unknown_name': Unknown name in syntax"):
        ParserGenerator.validate(grammar, set())


def test_extra_names() -> None:
    grammar = load_grammar("""
    start: extra_name
    """)
    ParserGenerator.validate(grammar, {"extra_name"})


def test_invalid_hanging_alts() -> None:
    grammar = dedent("""
    a:
        "1"
        | "2" | "3"
    """)
    assert isinstance(GrammarParser.from_text(grammar).start(), ParseFailure)
