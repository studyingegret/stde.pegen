# TODO: Split into smaller categorized test files

import ast
import difflib
import io
import sys
from textwrap import dedent
import token
from tokenize import NAME, NEWLINE, NUMBER, OP, TokenInfo
from typing import Any, Dict, Type, cast

from stde.pegen.v2.parser_generator import mark_left_recursives, mark_nullables
import pytest
from stde.pegen.v2.build import generate_parser_from_grammar, generate_parser_from_grammar, generate_code_from_grammar, load_grammar_from_string
from stde.pegen.v2.grammar_parser import GeneratedParser as GrammarParser
from stde.pegen.v2.parser import NO_MATCH, BaseParser, ParseFailure
from stde.pegen.v2.python_generator import PythonParserGenerator


def test_parse_grammar() -> None:
    grammar_source = dedent("""
    start: sum NEWLINE
    sum: t1=term '+' t2=term { action } | term
    term: NUMBER
    """)
    expected = dedent("""
    start: sum NEWLINE
    sum: term '+' term | term
    term: NUMBER
    """).strip()
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    assert str(grammar) == expected
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    rules = grammar.rules
    assert str(rules["start"]) == "start: sum NEWLINE"
    assert str(rules["sum"]) == "sum: term '+' term | term"
    expected_repr = "Rule('term', None, Rhs([Alt([TopLevelItem(None, NameLeaf('NUMBER'))])]))"
    assert repr(rules["term"]) == expected_repr


def test_parse_grammar_with_types() -> None:
    grammar_ = dedent("""
    start[ast.BinOp]: term ('+' term)* NEWLINE
    term[T[int]]: NUMBER
    c_rule[expr_ty*]: a=NUMBER? { _new_expr_ty(a) }
    """)
    grammar = GrammarParser.from_text(grammar_).start()
    assert not isinstance(grammar, ParseFailure)
    rules = grammar.rules
    assert rules["start"].type.replace(" ", "") == "ast.BinOp" #type:ignore
    assert rules["term"].type.replace(" ", "") == "T[int]" #type:ignore
    assert rules["c_rule"].type == "expr_ty*"


def test_long_rule_str() -> None:
    grammar_ = dedent("""
    start: zero | one | one zero | one one | one zero zero | one zero one | one one zero | one one one
    """)
    expected = """
    start:
        | zero
        | one
        | one zero
        | one one
        | one zero zero
        | one zero one
        | one one zero
        | one one one
    """
    grammar = GrammarParser.from_text(grammar_).start()
    assert not isinstance(grammar, ParseFailure)
    assert str(grammar.rules["start"]) == dedent(expected).strip()


def test_typed_rules() -> None:
    grammar_ = dedent("""
    start[int]: sum NEWLINE
    sum[int]: t1=term '+' t2=term { action } | term
    term[int]: NUMBER
    """)
    grammar = GrammarParser.from_text(grammar_).start()
    assert not isinstance(grammar, ParseFailure)
    rules = grammar.rules
    # Check the str() and repr() of a few rules; AST nodes don't support ==.
    assert str(rules["start"]) == "start: sum NEWLINE"
    assert str(rules["sum"]) == "sum: term '+' term | term"
    assert (repr(rules["term"])
        == "Rule('term', 'int', Rhs([Alt([TopLevelItem(None, NameLeaf('NUMBER'))])]))")


def test_gather() -> None:
    grammar = dedent("""
    start: ','.thing+ NEWLINE
    thing: NUMBER
    """)
    grammar_obj = GrammarParser.from_text(grammar).start()
    assert not isinstance(grammar_obj, ParseFailure)
    rules = grammar_obj.rules
    assert str(rules["start"]) == "start: ','.thing+ NEWLINE"
    print(repr(rules["start"]))
    assert repr(rules["start"]).startswith(
        "Rule('start', None, Rhs([Alt([TopLevelItem(None, Gather(StringLeaf(\"','\"), NameLeaf('thing'"
    )
    assert str(rules["thing"]) == "thing: NUMBER"
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("42\n").start()
    assert node == [
        [TokenInfo(NUMBER, string="42", start=(1, 0), end=(1, 2), line="42\n")],
        TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="42\n"),
    ]
    node = parser_class.from_text("1, 2, 3\n").start()
    assert node == [
        [
            TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1, 2, 3\n"),
            TokenInfo(NUMBER, string="2", start=(1, 3), end=(1, 4), line="1, 2, 3\n"),
            TokenInfo(NUMBER, string="3", start=(1, 6), end=(1, 7), line="1, 2, 3\n"),
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 7), end=(1, 8), line="1, 2, 3\n"),
    ]


def test_optional_operator() -> None:
    grammar = dedent("""
    start: sum NEWLINE
    sum: term ('+' term)?
    term: NUMBER
    """)
    parser_class = (p := generate_parser_from_grammar(grammar)).parser_class
    print(p.parser_code)
    node = parser_class.from_text("1+2\n").start()
    assert node == [
        [
            TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1+2\n"),
            [
                TokenInfo(OP, string="+", start=(1, 1), end=(1, 2), line="1+2\n"),
                TokenInfo(NUMBER, string="2", start=(1, 2), end=(1, 3), line="1+2\n"),
            ],
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 3), end=(1, 4), line="1+2\n"),
    ]
    node = parser_class.from_text("1\n").start()
    assert node == [
        [TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"), NO_MATCH],
        TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
    ]


def test_optional_literal() -> None:
    grammar = dedent("""
    start: sum NEWLINE
    sum: term '+' ?
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1+\n").start()
    assert node == [
        [
            TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1+\n"),
            TokenInfo(OP, string="+", start=(1, 1), end=(1, 2), line="1+\n"),
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="1+\n"),
    ]
    node = parser_class.from_text("1\n").start()
    assert node == [
        [TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"), NO_MATCH],
        TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
    ]


def test_alt_optional_operator() -> None:
    grammar = dedent("""
    start: sum NEWLINE
    sum: term ['+' term]
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1 + 2\n").start()
    assert node == [
        [
            TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2\n"),
            [
                TokenInfo(OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2\n"),
                TokenInfo(NUMBER, string="2", start=(1, 4), end=(1, 5), line="1 + 2\n"),
            ],
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 + 2\n"),
    ]
    node = parser_class.from_text("1\n").start()
    assert node == [
        [TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"), NO_MATCH],
        TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
    ]


def test_repeat_0_simple() -> None:
    grammar = dedent("""
    start: thing thing* NEWLINE
    thing: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1 2 3\n").start()
    assert node == [
        TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 2 3\n"),
        [
            TokenInfo(NUMBER, string="2", start=(1, 2), end=(1, 3), line="1 2 3\n"),
            TokenInfo(NUMBER, string="3", start=(1, 4), end=(1, 5), line="1 2 3\n"),
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 2 3\n"),
    ]
    node = parser_class.from_text("1\n").start()
    assert node == [
        TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1\n"),
        [],
        TokenInfo(NEWLINE, string="\n", start=(1, 1), end=(1, 2), line="1\n"),
    ]


def test_repeat_0_complex() -> None:
    grammar = dedent("""
    start: term ('+' term)* NEWLINE
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1 + 2 + 3\n").start()
    assert node == [
        TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2 + 3\n"),
        [
            [
                TokenInfo(OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2 + 3\n"),
                TokenInfo(NUMBER, string="2", start=(1, 4), end=(1, 5), line="1 + 2 + 3\n"),
            ],
            [
                TokenInfo(OP, string="+", start=(1, 6), end=(1, 7), line="1 + 2 + 3\n"),
                TokenInfo(NUMBER, string="3", start=(1, 8), end=(1, 9), line="1 + 2 + 3\n"),
            ],
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"),
    ]


def test_repeat_1_simple() -> None:
    grammar = dedent("""
    start: thing thing+ NEWLINE
    thing: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1 2 3\n").start()
    assert node == [
        TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 2 3\n"),
        [
            TokenInfo(NUMBER, string="2", start=(1, 2), end=(1, 3), line="1 2 3\n"),
            TokenInfo(NUMBER, string="3", start=(1, 4), end=(1, 5), line="1 2 3\n"),
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 5), end=(1, 6), line="1 2 3\n"),
    ]
    assert isinstance(parser_class.from_text("1\n").start(), ParseFailure)


def test_repeat_1_complex() -> None:
    grammar = dedent("""
    start: term ('+' term)+ NEWLINE
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("1 + 2 + 3\n").start()
    assert node == [
        TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2 + 3\n"),
        [
            [
                TokenInfo(OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2 + 3\n"),
                TokenInfo(NUMBER, string="2", start=(1, 4), end=(1, 5), line="1 + 2 + 3\n"),
            ],
            [
                TokenInfo(OP, string="+", start=(1, 6), end=(1, 7), line="1 + 2 + 3\n"),
                TokenInfo(NUMBER, string="3", start=(1, 8), end=(1, 9), line="1 + 2 + 3\n"),
            ],
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"),
    ]
    assert isinstance(parser_class.from_text("1\n").start(), ParseFailure)


def test_left_recursive() -> None:
    grammar_source = dedent("""
    start: expr NEWLINE
    expr: ('-' term | expr '+' term | term)
    term: NUMBER
    foo: NAME+
    bar: NAME*
    baz: NAME?
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    rules = grammar.rules
    mark_left_recursives(rules)
    assert not rules["start"].left_recursive
    assert rules["expr"].left_recursive
    assert not rules["term"].left_recursive
    assert not rules["foo"].left_recursive
    assert not rules["bar"].left_recursive
    assert not rules["baz"].left_recursive

    parser_class = generate_parser_from_grammar(grammar_source).parser_class
    node = parser_class.from_text("1 + 2 + 3\n").start()
    assert node == [
        [
            [
                TokenInfo(NUMBER, string="1", start=(1, 0), end=(1, 1), line="1 + 2 + 3\n"),
                TokenInfo(OP, string="+", start=(1, 2), end=(1, 3), line="1 + 2 + 3\n"),
                TokenInfo(NUMBER, string="2", start=(1, 4), end=(1, 5), line="1 + 2 + 3\n"),
            ],
            TokenInfo(OP, string="+", start=(1, 6), end=(1, 7), line="1 + 2 + 3\n"),
            TokenInfo(NUMBER, string="3", start=(1, 8), end=(1, 9), line="1 + 2 + 3\n"),
        ],
        TokenInfo(NEWLINE, string="\n", start=(1, 9), end=(1, 10), line="1 + 2 + 3\n"),
    ]


def test_nullable() -> None:
    grammar_source = dedent("""
    start: sign NUMBER
    sign: ['-' | '+']
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    rules = grammar.rules
    mark_nullables(rules)
    assert rules["start"].nullable is False  # Not None!
    assert rules["sign"].nullable


def test_advanced_left_recursive() -> None:
    grammar_source = dedent("""
    start: NUMBER | sign start
    sign: ['-']
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    rules = grammar.rules
    mark_nullables(rules)
    assert rules["start"].nullable is False  # Not None!
    assert rules["sign"].nullable
    mark_left_recursives(rules)
    assert rules["start"].left_recursive
    assert not rules["sign"].left_recursive


def test_mutually_left_recursive() -> None:
    grammar_source = dedent("""
    start: foo 'E'
    foo: bar 'A' | 'B'
    bar: foo 'C' | 'D'
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar)
    rules = grammar.rules
    assert not rules["start"].left_recursive
    assert rules["foo"].left_recursive
    assert rules["bar"].left_recursive
    genr.generate(out, "<string>")
    ns: Dict[str, Any] = {}
    exec(out.getvalue(), ns)
    parser_class: Type[BaseParser] = ns["GeneratedParser"]
    node = parser_class.from_text("D A C A E").start()
    assert node == [
        [
            [
                [
                    TokenInfo(type=NAME, string="D", start=(1, 0), end=(1, 1), line="D A C A E"),
                    TokenInfo(type=NAME, string="A", start=(1, 2), end=(1, 3), line="D A C A E"),
                ],
                TokenInfo(type=NAME, string="C", start=(1, 4), end=(1, 5), line="D A C A E"),
            ],
            TokenInfo(type=NAME, string="A", start=(1, 6), end=(1, 7), line="D A C A E"),
        ],
        TokenInfo(type=NAME, string="E", start=(1, 8), end=(1, 9), line="D A C A E"),
    ]
    node = parser_class.from_text("B C A E").start()
    assert node is not None
    assert node == [
        [
            [
                TokenInfo(type=NAME, string="B", start=(1, 0), end=(1, 1), line="B C A E"),
                TokenInfo(type=NAME, string="C", start=(1, 2), end=(1, 3), line="B C A E"),
            ],
            TokenInfo(type=NAME, string="A", start=(1, 4), end=(1, 5), line="B C A E"),
        ],
        TokenInfo(type=NAME, string="E", start=(1, 6), end=(1, 7), line="B C A E"),
    ]


def test_nasty_mutually_left_recursive() -> None:
    # This grammar does not recognize 'x - + =', much to my chagrin.
    # But that's the way PEG works.
    # [Breathlessly]
    # The problem is that the toplevel target call
    # recurses into maybe, which recognizes 'x - +',
    # and then the toplevel target looks for another '+',
    # which fails, so it retreats to NAME,
    # which succeeds, so we end up just recognizing 'x',
    # and then start fails because there's no '=' after that.
    grammar_source = dedent("""
    start: target '='
    target: maybe '+' | NAME
    maybe: maybe '-' | target
    """)
    grammar = GrammarParser.from_text(grammar_source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar)
    genr.generate(out, "<string>")
    ns: Dict[str, Any] = {}
    exec(out.getvalue(), ns)
    parser_class = ns["GeneratedParser"]
    assert isinstance(parser_class.from_text("x - + =").start(), ParseFailure)


def test_lookahead() -> None:
    grammar = dedent("""
    start: (expr_stmt | assign_stmt) &'.'
    expr_stmt: !(target '=') expr
    assign_stmt: target '=' expr
    expr: term ('+' term)*
    target: NAME
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("foo = 12 + 12 .").start()
    assert node == [
        TokenInfo(NAME, string="foo", start=(1, 0), end=(1, 3), line="foo = 12 + 12 ."),
        TokenInfo(OP, string="=", start=(1, 4), end=(1, 5), line="foo = 12 + 12 ."),
        [
            TokenInfo(NUMBER, string="12", start=(1, 6), end=(1, 8), line="foo = 12 + 12 ."),
            [
                [
                    TokenInfo(OP, string="+", start=(1, 9), end=(1, 10), line="foo = 12 + 12 ."),
                    TokenInfo(
                        NUMBER, string="12", start=(1, 11), end=(1, 13), line="foo = 12 + 12 ."
                    ),
                ]
            ],
        ],
    ]


def test_named_lookahead_error() -> None:
    grammar = dedent("""
    start: foo=!'x' NAME
    """)
    with pytest.raises(SyntaxError):
        generate_parser_from_grammar(grammar).parser_class


def test_start_leader() -> None:
    grammar = dedent("""
    start: attr | NAME
    attr: start '.' NAME
    """)
    # Would assert False without a special case in compute_left_recursives().
    generate_parser_from_grammar(grammar)


def test_left_recursion_too_complex() -> None:
    grammar = dedent("""
    start: foo
    foo: bar '+' | baz '+' | '+'
    bar: baz '-' | foo '-' | '-'
    baz: foo '*' | bar '*' | '*'
    """)
    with pytest.raises(ValueError) as errinfo:
        generate_parser_from_grammar(grammar).parser_class
    assert "no leader" in str(errinfo.value)


def test_cut() -> None:
    grammar = dedent("""
    start: '(' ~ NUMBER ')'
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("(1)").start()
    assert node == [
        TokenInfo(OP, string="(", start=(1, 0), end=(1, 1), line="(1)"),
        TokenInfo(NUMBER, string="1", start=(1, 1), end=(1, 2), line="(1)"),
        TokenInfo(OP, string=")", start=(1, 2), end=(1, 3), line="(1)"),
    ]


def test_cut_early_exit() -> None:
    grammar = dedent("""
    start: '(' ~ NUMBER ')' | '(' NAME ')'
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert isinstance(parser_class.from_text("(a)").start(), ParseFailure)


def test_soft_keyword() -> None:
    grammar = dedent("""
    start:
        | "number" n=NUMBER { eval(n.string) }
        | "string" n=STRING { n.string }
        | SOFT_KEYWORD l=NAME n=(NUMBER | NAME | STRING) { f"{l.string} = {n.string}"}
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("number 1").start() == 1
    assert parser_class.from_text("string 'b'").start() == "'b'"
    assert parser_class.from_text("number test 1").start() == "test = 1"
    assert parser_class.from_text("string test 'b'").start() == "test = 'b'"
    assert isinstance(parser_class.from_text("test 1").start(), ParseFailure)


def test_forced() -> None:
    grammar = dedent("""
    start: NAME &&':' | NAME
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("number :").start()
    assert "expected ':'" in str(parser_class.from_text("a").start().parse_exc)


def test_forced_with_group() -> None:
    grammar = dedent("""
    start: NAME &&(':' | ';') | NAME
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("number :").start()
    assert parser_class.from_text("number ;").start()
    res = parser_class.from_text("a").start()
    assert "expected (':' | ';')" in res.parse_exc.args[0]


UNREACHABLE = "None  # This is a test"


def test_unreachable_explicit() -> None:
    source = dedent("""
    start: NAME { UNREACHABLE }
    """)
    grammar = GrammarParser.from_text(source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, unreachable_formatting=UNREACHABLE)
    genr.generate(out, "<string>")
    assert UNREACHABLE in out.getvalue()


def test_unreachable_implicit1() -> None:
    source = dedent("""
    start: NAME | invalid_input
    invalid_input: NUMBER { None }
    """)
    grammar = GrammarParser.from_text(source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, unreachable_formatting=UNREACHABLE)
    genr.generate(out, "<string>")
    assert UNREACHABLE in out.getvalue()


def test_unreachable_implicit2() -> None:
    source = dedent("""
    start: NAME | '(' invalid_input ')'
    invalid_input: NUMBER { None }
    """)
    grammar = GrammarParser.from_text(source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, unreachable_formatting=UNREACHABLE)
    genr.generate(out, "<string>")
    assert UNREACHABLE in out.getvalue()


def test_unreachable_implicit3() -> None:
    source = dedent("""
    start: NAME | invalid_input { None }
    invalid_input: NUMBER
    """)
    grammar = GrammarParser.from_text(source).start()
    assert not isinstance(grammar, ParseFailure)
    out = io.StringIO()
    genr = PythonParserGenerator(grammar, unreachable_formatting=UNREACHABLE)
    genr.generate(out, "<string>")
    assert UNREACHABLE not in out.getvalue()


def test_locations() -> None:
    grammar = dedent("""
    @location_format "(start, end)"

    # sep consumes the final newline
    # so if sep matches, avoid matching NEWLINE (would be error)
    # (it's one of the cases that always having a NEWLINE at
    # end of input is annoying)
    start: items=sep.item+ (sep | NEWLINE) $ { (items, LOCATIONS) }
    item: "a" { LOCATIONS }
    sep: ("."|" "|NEWLINE)* "," ("."|" "|NEWLINE)*
    """)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert parser.from_text("a,   a  ,a,").start() == (
        [
            ((0, 0), (0, 1)),
            ((0, 5), (0, 6)),
            ((0, 9), (0, 10)),
        ],
        # Note: this was ((0, 0), (1, 0)) before.
        # But it is changed to what's convenient(?) due to bug fix.
        # (DefaultParser's natural behavior is to use the end pos
        # of the last parsed non-whitespace token as the end pos)
        # (TODO: Verify this statement)
        ((0, 0), (0, 11))
    )
    # "\n" + " " produces an INDENT token so we use "." instead
    assert parser.from_text("a,\na,\n..a,a,\n").start() == (
        [
            ((0, 0), (0, 1)),
            ((1, 0), (1, 1)),
            ((2, 2), (2, 3)),
            ((2, 4), (2, 5)),
        ],
        # XXX: Ending newline not included unlike previous sample?
        ((0, 0), (2, 6))
    )


def test_null_locations_1() -> None:
    grammar = dedent("""
    @location_format "(start, end)"
    start: $ { LOCATIONS }
    """)
    parser = generate_parser_from_grammar(grammar).parser_class
    assert parser.from_text("", verbose_stream=sys.stdout).start() == ((0, 0), (0, 0))


# Does not support match_string("")?
#def test_null_locations_2() -> None:
#    grammar = dedent("""
#    @location_format "(start, end)"
#    start: e NEWLINE $ { e + (LOCATIONS,) }
#    e: a1=a b a2=a { (a1, b, a2, LOCATIONS) }
#    a: "" { LOCATIONS }
#    b: "a" { LOCATIONS }
#    """)
#    parser = generate_parser_from_grammar(grammar).parser_class
#    assert parser.from_text("a", verbose_stream=sys.stdout).start() == (
#        ((0, 0), (0, 0)), # a (a1)
#        ((0, 0), (0, 1)), # b
#        ((0, 1), (0, 1)), # a (a2)
#        ((0, 0), (0, 1)), # e
#        ((0, 0), (1, 0))  # start
#    )


def test_null_locations_3() -> None:
    """Test without ENDMARKER"""
    grammar = dedent("""
    @location_format "(start, end)"
    start: { LOCATIONS }
    """)
    parser = (p:=generate_parser_from_grammar(grammar)).parser_class
    assert parser.from_text("", verbose_stream=sys.stdout).start() == ((0, 0), (0, 0))


def test_keywords() -> None:
    grammar = dedent("""
    start: 'one' 'two' 'three' 'four' 'five' "six" "seven" "eight" "nine" "ten"
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.KEYWORDS == ("five", "four", "one", "three", "two")
    assert parser_class.SOFT_KEYWORDS == ("eight", "nine", "seven", "six", "ten")


# Previously undocumented logic, now documented in README
def test_hard_keywords() -> None:
    grammar = dedent("""
    start: "hello" NAME | 'world'
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    parser = parser_class.from_text("hello world")
    assert isinstance(parser.start(), ParseFailure)
    assert parser.make_syntax_error("").args[1][1:] == (1, 7, 'hello world')
    assert not isinstance(parser_class.from_text("world").start(), ParseFailure)


def test_skip_actions() -> None:
    grammar = 'start: NAME { "pizza!!!" }'
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("hello").start() == "pizza!!!"
    parser_class = generate_parser_from_grammar(grammar, skip_actions=True).parser_class
    # Note: NAME returns TokenInfo
    assert (parser_class.from_text("hello").start()
            == TokenInfo(type=token.NAME, string="hello", start=(1, 0), end=(1, 5), line="hello"))


def test_hanging_alts() -> None:
    grammar_ = dedent("""
    a:
        "1" | "2" | "3"
    b: "1"
        | "2" | "3"
    c:
        | "1"
        | "2" | "3"
    """)
    grammar = GrammarParser.from_text(grammar_).start()
    assert not isinstance(grammar, ParseFailure)
    assert (str(grammar.rules["a"])[1:] == str(grammar.rules["a"])[1:] == str(grammar.rules["a"])[1:]
            == ': "1" | "2" | "3"')


# ---
# Sample grammars
# ---


def test_sample_expr_grammar() -> None:
    grammar = dedent("""
    start: sum NEWLINE
    sum: term '+' term | term
    term: NUMBER
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("42\n").start()
    assert node == [
        TokenInfo(NUMBER, string="42", start=(1, 0), end=(1, 2), line="42\n"),
        TokenInfo(NEWLINE, string="\n", start=(1, 2), end=(1, 3), line="42\n"),
    ]


def test_sample_python_expr() -> None:
    grammar = dedent("""
    @header '''
    import ast
    '''
    start: expr NEWLINE? $ { ast.Expression(expr, LOCATIONS) }
    expr: ( expr '+' term { ast.BinOp(expr, ast.Add(), term, LOCATIONS) }
          | expr '-' term { ast.BinOp(expr, ast.Sub(), term, LOCATIONS) }
          | term { term }
          )
    term: ( l=term '*' r=factor { ast.BinOp(l, ast.Mult(), r, LOCATIONS) }
          | l=term '/' r=factor { ast.BinOp(l, ast.Div(), r, LOCATIONS) }
          | factor { factor }
          )
    factor: ( '(' expr ')' { expr }
            | atom { atom }
            )
    atom: ( n=NAME { ast.Name(id=n.string, ctx=ast.Load(), LOCATIONS) }
          | n=NUMBER { ast.Constant(value=ast.literal_eval(n.string), LOCATIONS) }
          )
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    node = parser_class.from_text("(1 + 2*3 + 5)/(6 - 2)\n").start()
    assert not isinstance(node, ParseFailure)
    code = compile(node, "", "eval")
    val = eval(code)
    assert val == 3.0


def test_sample_with_locations() -> None:
    grammar = dedent("""
    @header '''
    import ast
    '''
    # Note: "start_colno - 1" is to match the default ast behavior
    @location_format "lineno=start_lineno + 1, col_offset=start_colno, end_lineno=end_lineno + 1, end_col_offset=end_colno"
    start: t=term NEWLINE $ { ast.Expression(t, LOCATIONS) }
    term:
        | l=term '*' r=factor { ast.BinOp(l, ast.Mult(), r, LOCATIONS) }
        | l=term '/' r=factor { ast.BinOp(l, ast.Div(), r, LOCATIONS) }
        | factor
    factor:
        | (
            n=NAME { ast.Name(id=n.string, ctx=ast.Load(), LOCATIONS) } |
            n=NUMBER { ast.Constant(value=ast.literal_eval(n.string), LOCATIONS) }
         )
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    source = "2*3\n"
    parsed = parser_class.from_text(source).start()
    assert not isinstance(parsed, ParseFailure)
    o = ast.dump(parsed.body, include_attributes=True)
    p = ast.dump(
        ast.parse(source).body[0].value, include_attributes=True #type:ignore
    ).replace(" kind=None,", "")
    diff = "\n".join(difflib.unified_diff(p.split("\n"), o.split("\n"), "cpython", "python-pegen"))
    if diff:
        print(diff)
    assert not diff
