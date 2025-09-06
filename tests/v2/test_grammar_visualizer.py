import textwrap
from typing import List
from textwrap import dedent
from stde.pegen.grammar_parser_v2 import GeneratedParser as GrammarParser
from stde.pegen.grammar_visualizer_v2 import ASTGrammarPrinter
from stde.pegen.parser_v2 import FAILURE


def test_simple_rule() -> None:
    grammar = dedent("""
    start: 'a' 'b'
    """)
    rules = GrammarParser.from_text(grammar).start()
    assert rules is not FAILURE

    printer = ASTGrammarPrinter()
    lines: List[str] = []
    printer.print_grammar_ast(rules, printer=lines.append)

    output = "\n".join(lines)
    expected_output = textwrap.dedent("""\
    └──Rule
       └──Rhs
          └──Alt
             ├──TopLevelItem
             │  └──StringLeaf("'a'")
             └──TopLevelItem
                └──StringLeaf("'b'")
    """)

    assert output == expected_output


def test_multiple_rules() -> None:
    grammar = dedent("""
    start: a b
    a: 'a'
    b: 'b'
    """)
    rules = GrammarParser.from_text(grammar).start()
    assert rules is not FAILURE

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
    grammar = dedent("""
    start: 'a' ['b'['c'['d']]]
    """)
    rules = GrammarParser.from_text(grammar).start()
    assert rules is not FAILURE

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
                   └──Group
                      └──Rhs
                         └──Alt
                            ├──TopLevelItem
                            │  └──StringLeaf("'b'")
                            └──TopLevelItem
                               └──Opt
                                  └──Group
                                     └──Rhs
                                        └──Alt
                                           ├──TopLevelItem
                                           │  └──StringLeaf("'c'")
                                           └──TopLevelItem
                                              └──Opt
                                                 └──Group
                                                    └──Rhs
                                                       └──Alt
                                                          └──TopLevelItem
                                                             └──StringLeaf("'d'")
                            """
    )

    assert output == expected_output
