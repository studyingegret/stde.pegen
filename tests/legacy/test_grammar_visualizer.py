import textwrap
from typing import List

from stde.pegen.grammar_parser import GeneratedParser as GrammarParser
from stde.pegen.grammar_visualizer import ASTGrammarPrinter
from stde.pegen.utils import parse_string


def test_simple_rule() -> None:
    grammar = """
    start: 'a' 'b'
    """
    rules = parse_string(grammar, GrammarParser)

    printer = ASTGrammarPrinter()
    lines: List[str] = []
    printer.print_grammar_ast(rules, printer=lines.append)

    output = "\n".join(lines)
    expected_output = textwrap.dedent(
        """\
    └──Rule
       └──Rhs
          └──Alt
             ├──TopLevelItem
             │  └──StringLeaf("'a'")
             └──TopLevelItem
                └──StringLeaf("'b'")
    """
    )

    assert output == expected_output


def test_multiple_rules() -> None:
    grammar = """
    start: a b
    a: 'a'
    b: 'b'
    """
    rules = parse_string(grammar, GrammarParser)

    printer = ASTGrammarPrinter()
    lines: List[str] = []
    printer.print_grammar_ast(rules, printer=lines.append)

    output = "\n".join(lines)
    expected_output = textwrap.dedent(
        """\
    └──Rule
       └──Rhs
          └──Alt
             ├──TopLevelItem
             │  └──NameLeaf('a')
             └──TopLevelItem
                └──NameLeaf('b')

    └──Rule
       └──Rhs
          └──Alt
             └──TopLevelItem
                └──StringLeaf("'a'")

    └──Rule
       └──Rhs
          └──Alt
             └──TopLevelItem
                └──StringLeaf("'b'")
                    """
    )

    assert output == expected_output


def test_deep_nested_rule() -> None:
    grammar = """
    start: 'a' ['b'['c'['d']]]
    """
    rules = parse_string(grammar, GrammarParser)

    printer = ASTGrammarPrinter()
    lines: List[str] = []
    printer.print_grammar_ast(rules, printer=lines.append)

    output = "\n".join(lines)
    print()
    print(output)
    expected_output = textwrap.dedent(
        """\
    └──Rule
       └──Rhs
          └──Alt
             ├──TopLevelItem
             │  └──StringLeaf("'a'")
             └──TopLevelItem
                └──Opt
                   └──Rhs
                      └──Alt
                         ├──TopLevelItem
                         │  └──StringLeaf("'b'")
                         └──TopLevelItem
                            └──Opt
                               └──Rhs
                                  └──Alt
                                     ├──TopLevelItem
                                     │  └──StringLeaf("'c'")
                                     └──TopLevelItem
                                        └──Opt
                                           └──Rhs
                                              └──Alt
                                                 └──TopLevelItem
                                                    └──StringLeaf("'d'")
                            """
    )

    assert output == expected_output
