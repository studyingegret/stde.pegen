from __future__ import annotations

from abc import ABC, abstractmethod
import itertools
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Generic,
    Iterable,
    Iterator,
    List,
    Never,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from stde.pegen.common import ValidationError # Also re-export

if TYPE_CHECKING:
    from stde.pegen.parser_generator import ParserGenerator


class GrammarError(Exception):
    pass


VisitReturnType = TypeVar("VisitReturnType", bound=Any, default=Any)

class GrammarVisitor(Generic[VisitReturnType]):
    """Code structure that traverses a node in depth-first order.
    It is intended to be used to traverse a Grammar but is not limited
    to Grammars.

    Supports specializing visiting a `node` by its `node.__class__.__name__`
    (see implementation for how to do it).

    Note: The default visitor, generic_visit, flattens items of 
    iterable nodes that are `list`s.
    """
    def visit(self, node: Any, *args: Any, **kwargs: Any) -> VisitReturnType:
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        #XXX: Viewing a node as non-scalar by whether it is iterable?
        visitor = getattr(self, method, self.generic_visit)
        return cast(VisitReturnType, visitor(node, *args, **kwargs))

    def generic_visit(self, node: Iterable[Any], *args: Any, **kwargs: Any) -> None:
        """Called if no explicit visitor function exists for a node."""
        #XXX: Viewing a node as non-scalar by whether it is iterable?
        if not hasattr(node, "__iter__"):
            raise ValueError("Doesn't know how to handle non-iterable node "
                             f"(type: {node.__class__.__name__}): {node!r}")
        for value in node:
            if isinstance(value, list):
                for item in value:
                    self.visit(item, *args, **kwargs)
            else:
                self.visit(value, *args, **kwargs)


def _check_duplicate_names(names: Iterable[str]) -> None:
    seen_names = set()
    for name in names:
        if name in seen_names:
            raise ValidationError(f"Duplicate name {name}")
        else:
            seen_names.add(name)



class Grammar:
    #def __init__(self, rules: Iterable[Rule], metas: Iterable[Tuple[str, Optional[str]]]):
    def __init__(self, rules: Iterable[Rule], extern_decls: Iterable[ExternDecl], metas: Any): #?
        rules = list(rules)
        extern_decls = list(extern_decls)
        _check_duplicate_names(itertools.chain(
            (rule.name for rule in rules),
            (extern_decl.name for extern_decl in extern_decls)
        ))
        self.rules = {rule.name: rule for rule in rules}
        self.extern_decls = {extern_decl.name: extern_decl for extern_decl in extern_decls}
        self.metas = dict(metas)
        self.items = self.rules | self.extern_decls

    def __getitem__(self, name: str) -> GrammarItem:
        return self.items[name]

    def __str__(self) -> str:
        return "\n".join(map(str, itertools.chain(self.rules.values(), self.extern_decls.values())))

    def __repr__(self) -> str:
        return "\n".join(itertools.chain([
            "Grammar(",
            "  ["
        ], (f"    {repr(rule)}," for rule in self.rules.values()), [
            "  ],"
        ], (f"    {repr(extern_decl)}" for extern_decl in self.extern_decls.values()), [
            f"  {repr(list(self.metas.items()))}",
            ")"
        ]))

    def __iter__(self) -> Iterator[Rule]: #XXX: Include extern_decls?
        return iter(self.rules.values())


# Global flag whether we want actions in __str__() -- default off.
SIMPLE_STR = True


class Rule:
    def __init__(self, name: str, type: Optional[str], rhs: Rhs, memo: Optional[object] = None):
        self.name = name
        self.type = type
        self.rhs = rhs
        self.memo = bool(memo)
        #self.visited = False #unused
        self.nullable = False
        self.left_recursive = False
        self.leader = False

    def is_loop(self) -> bool:
        return self.name.startswith("_loop")

    def is_gather(self) -> bool:
        return self.name.startswith("_gather")

    def __str__(self) -> str:
        if SIMPLE_STR or self.type is None:
            res = f"{self.name}: {self.rhs}"
        else:
            res = f"{self.name}[{self.type}]: {self.rhs}"
        if len(res) < 88:
            return res
        lines = [res.split(":")[0] + ":"]
        lines += [f"    | {alt}" for alt in self.rhs.alts]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"Rule({self.name!r}, {self.type!r}, {self.rhs!r})"

    def __iter__(self) -> Iterator[Rhs]:
        return iter([self.rhs])

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()

    def flatten(self) -> Rhs:
        # If it's a single parenthesized group, flatten it.
        rhs = self.rhs
        if (
            not self.is_loop()
            and len(rhs.alts) == 1
            and len(rhs.alts[0].items) == 1
            and isinstance(rhs.alts[0].items[0].item, Group)
        ):
            rhs = rhs.alts[0].items[0].item.rhs
        return rhs

    #XXX: What does this do?
    def collect_todo(self, gen: ParserGenerator) -> None:
        rhs = self.flatten()
        rhs.collect_todo(gen)


class ExternDecl:
    def __init__(self, name: str, type: Optional[str]):
        self.name = name
        self.type = type

    def __str__(self):
        return f"extern {self.name}" + (f"[{self.type}]" if self.type else "")

    def __repr__(self) -> str:
        return f"ExternDecl({self.name!r}, {self.type!r})"

    # Don't make an error if GrammarVisitor doesn't process it
    def __iter__(self) -> Iterable[Never]:
        return iter([])


class Leaf:
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __iter__(self) -> Iterable[Never]:
        return iter([])

    @abstractmethod
    def initial_names(self) -> AbstractSet[str]: ...


class NameLeaf(Leaf):
    """The value is the name."""

    def __str__(self) -> str:
        if self.value == "ENDMARKER":
            return "$"
        return super().__str__()

    def __repr__(self) -> str:
        return f"NameLeaf({self.value!r})"

    def initial_names(self) -> AbstractSet[str]:
        return {self.value}


class StringLeaf(Leaf):
    """The value is a string literal, including quotes."""

    def __repr__(self) -> str:
        return f"StringLeaf({self.value!r})"

    def initial_names(self) -> AbstractSet[str]:
        return set()


class Rhs:
    def __init__(self, alts: List[Alt]):
        self.alts = alts
        self.memo: Optional[Tuple[Optional[str], str]] = None

    def __str__(self) -> str:
        return " | ".join(str(alt) for alt in self.alts)

    def __repr__(self) -> str:
        return f"Rhs({self.alts!r})"

    def __iter__(self) -> Iterator[List[Alt]]:
        return iter([self.alts])

    def initial_names(self) -> AbstractSet[str]:
        names: Set[str] = set()
        for alt in self.alts:
            names |= alt.initial_names()
        return names

    #XXX: What does this do?
    def collect_todo(self, gen: ParserGenerator) -> None:
        for alt in self.alts:
            alt.collect_todo(gen)


class Alt:
    #XXX: icut currently unused? (Not even in metagrammar.gram)
    #XXX: Purpose of icut?
    def __init__(self, items: List[TopLevelItem], *, icut: int = -1, action: Optional[str] = None):
        self.items = items
        self.icut = icut
        self.action = action

    def __str__(self) -> str:
        core = " ".join(str(item) for item in self.items)
        if not SIMPLE_STR and self.action:
            return f"{core} {{ {self.action} }}"
        else:
            return core

    def __repr__(self) -> str:
        args = [repr(self.items)]
        if self.icut >= 0:
            args.append(f"icut={self.icut}")
        if self.action is not None:
            args.append(f"action={self.action!r}")
        return f"Alt({', '.join(args)})"

    def __iter__(self) -> Iterator[List[TopLevelItem]]:
        return iter([self.items])

    def initial_names(self) -> AbstractSet[str]:
        names: Set[str] = set()
        for item in self.items:
            names |= item.initial_names()
            if not item.nullable:
                break
        return names

    #XXX: What does this do?
    def collect_todo(self, gen: ParserGenerator) -> None:
        for item in self.items:
            item.collect_todo(gen)


class TopLevelItem:
    """An Item, possibly named, and possibly with a type when named.
    Called TopLevelItem because it is the top-level item type of Alt. (?)
    """
    def __init__(self, name: Optional[str], item: Item, type: Optional[str] = None):
        self.name = name
        self.item = item
        self.type = type
        self.nullable = False #TODO: Doc

    def __str__(self) -> str:
        if not SIMPLE_STR and self.name:
            return f"{self.name}={self.item}"
        else:
            return str(self.item)

    def __repr__(self) -> str:
        return f"TopLevelItem({self.name!r}, {self.item!r})"

    def __iter__(self) -> Iterator[Item]:
        return iter([self.item])

    def initial_names(self) -> AbstractSet[str]:
        return self.item.initial_names()

    #XXX: What does this do?
    def collect_todo(self, gen: ParserGenerator) -> None:
        # I've tested that it is not invoked by the tests.
        raise NotImplementedError("collect_todo looks like a TODO feature.")
        gen.callmakervisitor.visit(self.item)


class Forced:
    """&&node"""
    def __init__(self, node: Plain):
        self.node = node

    def __str__(self) -> str:
        return f"&&{self.node}"

    def __iter__(self) -> Iterator[Plain]:
        return iter([self.node])

    def initial_names(self) -> AbstractSet[str]:
        return set()


class Lookahead:
    def __init__(self, node: Plain, sign: str):
        self.node = node
        self.sign = sign

    def __str__(self) -> str:
        return f"{self.sign}{self.node}"

    def __iter__(self) -> Iterator[Plain]:
        return iter([self.node])

    def initial_names(self) -> AbstractSet[str]:
        return set()


class PositiveLookahead(Lookahead):
    """&node"""
    def __init__(self, node: Plain):
        super().__init__(node, "&")

    def __repr__(self) -> str:
        return f"PositiveLookahead({self.node!r})"


class NegativeLookahead(Lookahead):
    """!node"""
    def __init__(self, node: Plain):
        super().__init__(node, "!")

    def __repr__(self) -> str:
        return f"NegativeLookahead({self.node!r})"


class Opt:
    """[node], node?"""
    def __init__(self, node: Item):
        self.node = node

    def __str__(self) -> str:
        s = str(self.node)
        # TODO: Decide whether to use [X] or X? based on type of X
        if " " in s:
            return f"[{s}]"
        else:
            return f"{s}?"

    def __repr__(self) -> str:
        return f"Opt({self.node!r})"

    def __iter__(self) -> Iterator[Item]:
        return iter([self.node])

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat:
    """Shared base class for x* and x+."""
    def __init__(self, node: Plain):
        self.node = node
        self.memo: Optional[Tuple[Optional[str], str]] = None

    def __iter__(self) -> Iterator[Plain]:
        return iter([self.node])

    def initial_names(self) -> AbstractSet[str]:
        return self.node.initial_names()


class Repeat0(Repeat):
    """node*"""
    def __str__(self) -> str:
        s = str(self.node)
        # TODO: Decide whether to use (X)* or X* based on type of X
        if " " in s:
            return f"({s})*"
        else:
            return f"{s}*"

    def __repr__(self) -> str:
        return f"Repeat0({self.node!r})"


class Repeat1(Repeat):
    """node+"""
    def __str__(self) -> str:
        s = str(self.node)
        # TODO: Decide whether to use (X)+ or X+ based on type of X
        # ^ XXX: How exactly?
        if " " in s:
            return f"({s})+"
        else:
            return f"{s}+"

    def __repr__(self) -> str:
        return f"Repeat1({self.node!r})"


class Gather(Repeat):
    """separator.node+"""
    def __init__(self, separator: Plain, node: Plain):
        self.separator = separator
        self.node = node

    def __str__(self) -> str:
        return f"{self.separator!s}.{self.node!s}+"

    def __repr__(self) -> str:
        return f"Gather({self.separator!r}, {self.node!r})"


class Group:
    """(rhs)"""
    def __init__(self, rhs: Rhs):
        self.rhs = rhs

    def __str__(self) -> str:
        return f"({self.rhs})"

    def __repr__(self) -> str:
        return f"Group({self.rhs!r})"

    def __iter__(self) -> Iterator[Rhs]:
        return iter([self.rhs])

    def initial_names(self) -> AbstractSet[str]:
        return self.rhs.initial_names()


class Cut:
    """~"""
    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "Cut()"

    def __str__(self) -> str:
        return "~"

    def __iter__(self) -> Iterator[Never]:
        return iter([])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cut):
            return NotImplemented
        return True

    def initial_names(self) -> AbstractSet[str]:
        return set()


Plain = Union[Leaf, Group]
Item = Union[Plain, Opt, Repeat, Forced, Lookahead, Rhs, Cut]
GrammarItem = Union[Rule, ExternDecl]
RuleName = Tuple[str, Optional[str]]
MetaTuple = Tuple[str, Optional[str]]
LookaheadOrCut = Union[Lookahead, Forced, Cut]
