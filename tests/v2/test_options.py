import pytest
from textwrap import dedent
from typing import Any
from stde.pegen.v2.parser import ParseFailure
from stde.pegen.v2.build import generate_parser_from_grammar


def test_exec_ns() -> None:
    grammar = dedent("""
    @header '''
    def it(x):
        a.append(10)
        return a + [x]
    it(None)
    '''
    start: NAME { it(name.string) }
    """)
    exec_ns: dict[str, Any] = {"a": []}
    parser_class = generate_parser_from_grammar(grammar, exec_ns=exec_ns).parser_class
    assert exec_ns["a"] == [10]
    assert parser_class.from_text("the").start() == [10, 10, "the"]
    assert parser_class.from_text("the").start() == [10, 10, 10, "the"]


def test_parseerror() -> None:
    grammar = dedent("""
    @header '''
    def it(x):
        if x == "a":
            raise ValueError("message")
        elif x == "b":
            raise SyntaxError("message")
        else:
            raise ParseError("message")
    '''
    start: NAME { it(name.string) }
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    with pytest.raises(ValueError, match="message"):
        parser_class.from_text("a").start()
    with pytest.raises(SyntaxError, match="message"):
        parser_class.from_text("b").start()
    res = parser_class.from_text("c").start()
    assert isinstance(res, ParseFailure)
    assert res.parse_exc.args == ("message",) #type:ignore