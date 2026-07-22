"""Statements in actions: Write statements, not confined to a single expression"""

import sys
import pytest
from textwrap import dedent
from stde.pegen.v2.build import generate_parser_from_grammar, ParseFailure

# TODO: Parameterize to also support @base CharBasedParser

@pytest.mark.skip("todo")
def test_return_stmt_simple() -> None:
    grammar = dedent("""
    start: a {
        if a == "a":
            return "Welcome back, a!"
        parts = []
        for char in a:
            if char != "a":
                parts.append(char)
                parts.append(char)
        return "".join(parts)
    }
    a: NAME { name.string }
    """)
    parser_class = generate_parser_from_grammar(grammar, parser_verbose_stream=sys.stdout).parser_class
    assert parser_class.from_text("a").start() == "Welcome back, a!"
    assert parser_class.from_text("abca").start() == "bbcc"

@pytest.mark.skip("todo")
def test_return_stmt_with_various_alt_formatting() -> None:
    """`}` doesn't have to be followed by content
    but `|` must be

    Note: `}` can escape indent requirements to align the `|`,
    as tested in test_return_stmt_with_hanging_right_brace.

    But `|` cannot do this.
    """
    grammar = dedent("""
    start:
        | a1=a a2=a {
            parts = []
            for char in a:
                if char in a1 and char not in a2:
                    parts.append(char)
            return "".join(parts)
        # Intentionally mixing many styles
        } | a {
           if a == "a":
               return "Welcome back, a!"
           parts = []
           for char in a:
               if char != "a":
                   parts.append(char)
                   parts.append(char)
           return "".join(parts)
        }
        | n1=n n2=n n3=n n4=n { int(n1 + n2 + n3 + n4)
                       + 100 # o.O?
        } # Wow here's a comment!

        # Wow here's another comment!
        | n1=n n2=n n3=n {
           int(
                n1 + n2 + n3
        ) }
        | n1=n n2=n { return int(
                n1 + n2
        ) }
        | n {
          # Here you cannot omit the brackets because the return statement
          # is just a statement and has to follow statement rules
          return ("Single number literal: "
                  + n)
        }
    a: NAME { name.string }
    n: NUMBER { number.string }
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("excellent exc").start() == "llnt"
    assert parser_class.from_text("a").start() == "Welcome back, a!"
    assert parser_class.from_text("abca").start() == "bbcc"
    assert parser_class.from_text("1 2 3 4").start() == "1334"
    assert parser_class.from_text("1 2 3").start() == "123"
    assert parser_class.from_text("1").start() == "Thankfully, it's the end"

    grammar = dedent("""
    start:
        # Forbidden even if indent is actually okay
        # (would be harder to maintain, see next)
        | n{a = n + n
            return a
        }
        # Code blocks are sequences of statements
        # and just have to follow sequence of statements' rules
        | n1=n n2=n { a = n1 + n2
            return a
        }
    a: NAME { name.string }
    n: NUMBER { number.string }
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class

@pytest.mark.skip("todo")
def test_raise_stmt() -> None:
    grammar = dedent("""
    start: "a" "a" {
        # TODO: Use specialized exceptions
        raise Exception
      } | a "a" {
        if a == "b":
            raise Exception
        return a + "a"
      }
    a: NAME { name.string }
    """)
    parser_class = generate_parser_from_grammar(grammar).parser_class
    #TODO