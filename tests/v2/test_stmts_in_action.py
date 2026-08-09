r"""Statements in actions: Write statements, not confined to a single expression

Valid:

rule: {
    if a:
        statements
        return ...
    if b:
        statements
    else:
        statements
    return ...
}

only_common_indent_matters: {
    a = '''The answer to the
    Ultimate Question of Life,
    the Universe and everything'''
    # `a` is "The answer to the\nUltimate Question of Life,\nthe Universe and everything"
    return a
}

Not valid:
- action start on left brace

      rule: { ...
          ...
          return ...
      }

    * test_starting_at_same_line_as_left_brace_fails_at_grammar_parsing_phase

- invalid indentation

      rule: {
          a = '''The answer to the
        Ultimate Question of Life,
           the Universe and everything'''
          return a
      }
      # OK at parse time: removes only common indent during parsing
      # Parses as action "  a = '''The answer to the\nUltimate Question of Life,\n   the Universe and everything'''\n  return a"
      # Fails at code generation phase

- mixing tabs and spaces in the common indent

      # "[\t]" = tab " " = space
      rule: { ...
      [\t]if 'answer' in '''The answer to the
      [\t] [\t] Ultimate Question of Life,
      [\t] the Universe and everything''':
      [\t][\t]  ...
      }
      # OK at parse time: parses as "if 'answer' in '''The answer to the\n [\t] Ultimate Question of Life,\n the Universe and everything''':\n[\t]  ..."
      # Fails at code generation phase due to the mixed "[\t]  " on the last line
      rule: { ...
       [\t] return a
      }
      # Fails at parse time even if it's only a single line (" [\t] " is the common indent)
      rule: { ...
      [\t]a = '''The answer to the
      [\t] [\t] Ultimate Question of Life,
      [\t][\t] the Universe and everything'''
      [\t]return a
      }
      # OK: a == "The answer to the\n [\t] Ultimate Question of Life,\n[\t] the Universe and everything"

Note: Behavior of

    rule: {
        '''The answer to the
        Ultimate Question of Life,
        the Universe and everything'''
    }

and

    rule: {
        return '''The answer to the
        Ultimate Question of Life,
        the Universe and everything'''
    }

is different since the former has "(...)\n    Ultimate(...)" and the latter has "(...)\nUltimate(...)"

So might be useful to allow stmts action start on line of left brace?

(And we can give a warning for the previous case, that triple-strings are problematic)
"""

import sys
from typing import Iterable
import pytest
from textwrap import dedent

from stde.pegen.v2.python_generator import ASTParseError

from stde.pegen.v2.parser import ParseError

from stde.pegen.v2.grammar import Grammar
from stde.pegen.v2.build import generate_code_from_grammar, generate_parser_from_grammar, load_grammar_from_string

# TODO: Parameterize to also support @base CharBasedParser (?)

#def grammars(s: Iterable[str]) -> Iterable[Grammar]:
#    return map(lambda s: load_grammar_from_string(s).grammar, s)

def test_return_stmt_simple() -> None:
    grammar_ = dedent("""
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
    grammar = load_grammar_from_string(grammar_, parser_verbose_stream=sys.stdout).grammar
    print(repr(grammar))
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("a").start() == "Welcome back, a!"
    assert parser_class.from_text("abca").start() == "bbcc"

@pytest.mark.parametrize("grammar", [
    "start: { return 42 }",
    dedent("""
    start: {if 1:
                return 42
            else:
                return 24
    }
    """),
    dedent("""
    start: {if 1:
                return 42
            else:
                return 24}
    """),
])
def test_starting_at_same_line_as_left_brace_fails_at_grammar_parsing_phase(grammar: str) -> None:
    with pytest.raises(ParseError, match=".*cannot start on the same line as the left brace.*"): # TODO: Make an exception type
        load_grammar_from_string(grammar, parser_verbose_stream=sys.stdout)

@pytest.mark.parametrize("grammar", [
    dedent("""
    start: {
            a = 1
        return a
    }
    """),
    dedent("""
    start: {
    a = 1
        return a
    }
    """),
    dedent("""
    start: NAME {
        if name.string == "it":
            return 10
        else:
        \treturn 20
    }
    """),
])
def test_invalid_effective_indent_fails_at_code_generation_phase(grammar: str) -> None: # non-common indent = effective indent
    p = load_grammar_from_string(grammar, parser_verbose_stream=sys.stdout)
    with pytest.raises(ASTParseError): # TODO: Make an exception type
        generate_code_from_grammar(p.grammar)

@pytest.mark.parametrize("grammar", [
    dedent("""
    start: NAME {
    \t\t\tif name.string == "it":
    \t\t\t   return 10
    \t\t\telse:
    \t\t\t   return 20
    }
    """),
    dedent("""
    start: NAME {
    if name.string == "it":
       return 10
    else:
       return 20
    }
    """),
])
def test_non_mixed_common_indent_doesnt_matter(grammar: str) -> None:
    parser_class = generate_parser_from_grammar(grammar, parser_verbose_stream=sys.stdout).parser_class
    assert parser_class.from_text("it").start() == 10
    assert parser_class.from_text("not_it").start() == 20

@pytest.mark.parametrize("grammar", [
    dedent("""
    start: {
    \t return 1
    }
    """),
    dedent("""
    start: {
     \tif name.string == "it":
     \t   return 10
     \telse:
     \t   return 20
    }
    """),
    dedent("""
    start: {
      return (42 if True
    \t\telse 24)
    }
    """),
    dedent("""
    start: {
       return (42 if True
    \t        else 24)
    }
    """),
    dedent("""
    start: {
    \t\treturn (42 if True
    \t        else 24)
    }
    """),
])
def test_mixed_common_indent_fails_code_generation_phase(grammar: str) -> None:
    p = load_grammar_from_string(grammar, parser_verbose_stream=sys.stdout)
    with pytest.raises(ASTParseError): # TODO: Make an exception type
        generate_code_from_grammar(p.grammar)

@pytest.mark.parametrize("grammar", [
    dedent("""
    start: {
        return 10}
    """)
])
def test_brace_immediately_after_action_is_ok(grammar: str) -> None:
    parser_class = generate_parser_from_grammar(grammar).parser_class
    assert parser_class.from_text("").start() == 10