"""
Kernel YAML loader — reads YAML the way faf-kernel does.

faf-kernel (Rust) parses with serde_yaml_ng 0.10 into a ``serde_yaml_ng::Value``.
PyYAML's ``safe_load`` differs from that in ways that move scores (YAML 1.1
merge keys, silent duplicate keys, YAML 1.1 scalar types, unknown-tag errors),
so the scorer does not use it. This module scans with a port of libyaml's
scanner (``_libyaml_scanner``), parses with PyYAML's parser on top of it, and
rebuilds the value from the event stream exactly as serde_yaml_ng's
``DeserializerFromEvents`` + ``Value`` visitor do:

- first document only; a second document is an error
- no ``<<`` merge — it is an ordinary key
- a duplicate mapping key is an error
- plain scalars resolve with the YAML 1.2 core rules serde_yaml_ng uses
- ``!!bool`` / ``!!int`` / ``!!float`` / ``!!null`` must parse or it is an error;
  any other global tag (``!!str``, ``!!binary``, ``tag:...``) reads as a string
- a local tag (``!foo``, or the bare ``!``) wraps the value in :class:`Tagged`
- nesting deeper than 128 collections is an error (the scanner stops at
  flow level 129, so deep ``[``/``{`` input fails in linear time)
- alias expansion past ``100 × events`` jumps is an error ("repetition limit")
- anchor ids follow serde_yaml_ng: a redefined name can hand its id to a later
  anchor, and an alias resolves to the last node registered under its id
- an empty ``?`` key inside ``[...]`` also consumes the next token, as libyaml
  does, so ``[?, a]`` / ``[?]`` are errors

Any error raises :class:`KernelYamlError`.
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml
import yaml.parser
from yaml import events as ev

from ._libyaml_scanner import LibyamlScanner

_TAG_BOOL = "tag:yaml.org,2002:bool"
_TAG_INT = "tag:yaml.org,2002:int"
_TAG_FLOAT = "tag:yaml.org,2002:float"
_TAG_NULL = "tag:yaml.org,2002:null"

_MAX_DEPTH = 128  # serde_yaml_ng remaining_depth
_JUMP_FACTOR = 100  # serde_yaml_ng: jumpcount > events.len() * 100


class KernelYamlError(ValueError):
    """The kernel cannot read this YAML (it would return a parse error)."""


class Tagged:
    """A value carrying a local YAML tag (serde_yaml_ng ``Value::Tagged``)."""

    __slots__ = ("tag", "value")

    def __init__(self, tag: str, value: Any) -> None:
        self.tag = tag
        self.value = value


class Mapping(dict):  # type: ignore[type-arg]
    """A YAML mapping. Keys are :func:`_key` forms so equality follows
    serde_yaml_ng ``Value`` (``1`` != ``1.0`` != ``true`` != ``"1"``)."""


def untag(value: Any) -> Any:
    """serde_yaml_ng ``Value::untag_ref``."""
    while isinstance(value, Tagged):
        value = value.value
    return value


def str_key(name: str) -> Tuple[str, str]:
    """Mapping key form of a string (for slot lookups)."""
    return ("s", name)


def _key(value: Any) -> Any:
    """Hashable form of a value with serde_yaml_ng ``Value`` equality."""
    if value is None:
        return ("n",)
    if isinstance(value, bool):
        return ("b", value)
    if isinstance(value, int):
        return ("i", value)
    if isinstance(value, float):
        return ("f", "nan" if math.isnan(value) else value)
    if isinstance(value, str):
        return ("s", value)
    if isinstance(value, list):
        return ("l", tuple(_key(v) for v in value))
    if isinstance(value, Tagged):
        # serde_yaml_ng Tag equality ignores one leading "!"
        tag = value.tag[1:] if value.tag.startswith("!") else value.tag
        return ("t", tag, _key(value.value))
    if isinstance(value, dict):
        return ("m", frozenset((k, _key(v)) for k, v in value.items()))
    raise KernelYamlError("unhashable key")  # pragma: no cover


# --- scalar resolution (serde_yaml_ng de.rs) --------------------------------

_DIGITS = {2: frozenset("01"), 8: frozenset("01234567"),
           10: frozenset("0123456789"), 16: frozenset("0123456789abcdefABCDEF")}
_U64_MAX = 2**64 - 1
_I64_MIN = -(2**63)
_U128_MAX = 2**128 - 1
_I128_MIN = -(2**127)
_RUST_F64 = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def _from_str_radix(s: str, radix: int, signed: bool, lo: int, hi: int) -> Optional[int]:
    """Rust ``{u,i}N::from_str_radix``: optional sign, digits only, in range."""
    body = s
    neg = False
    if body[:1] == "+":
        body = body[1:]
    elif body[:1] == "-" and signed:
        body = body[1:]
        neg = True
    if not body or any(c not in _DIGITS[radix] for c in body):
        return None
    n = int(body, radix)
    if neg:
        n = -n
    return n if lo <= n <= hi else None


def _digits_but_not_number(s: str) -> bool:
    t = s[1:] if s[:1] in ("-", "+") else s
    return len(t) > 1 and t[0] == "0" and all(c in "0123456789" for c in t[1:])


def _parse_unsigned(s: str, hi: int) -> Optional[int]:
    unpositive = s[1:] if s[:1] == "+" else s
    for prefix, radix in (("0x", 16), ("0o", 8), ("0b", 2)):
        if unpositive.startswith(prefix):
            rest = unpositive[2:]
            if rest[:1] in ("+", "-"):
                return None
            n = _from_str_radix(rest, radix, False, 0, hi)
            if n is not None:
                return n
    if unpositive[:1] in ("+", "-"):
        return None
    if _digits_but_not_number(s):
        return None
    return _from_str_radix(unpositive, 10, False, 0, hi)


def _parse_negative(s: str, lo: int, hi: int) -> Optional[int]:
    for prefix, radix in (("-0x", 16), ("-0o", 8), ("-0b", 2)):
        if s.startswith(prefix):
            n = _from_str_radix("-" + s[3:], radix, True, lo, hi)
            if n is not None:
                return n
    if _digits_but_not_number(s):
        return None
    return _from_str_radix(s, 10, True, lo, hi)


def _parse_int(s: str) -> Optional[int]:
    """serde_yaml_ng ``visit_int``: u64, i64, then u128, i128.

    ``Value`` has no 128-bit numbers, so an integer that only fits u128/i128
    is an error ("invalid type: integer ..."), not a float or a string.
    """
    n = _parse_unsigned(s, _U64_MAX)
    if n is None:
        n = _parse_negative(s, _I64_MIN, 2**63 - 1)
    if n is not None:
        return n
    if _parse_unsigned(s, _U128_MAX) is not None or \
            _parse_negative(s, _I128_MIN, 2**127 - 1) is not None:
        raise KernelYamlError("invalid type: 128-bit integer")
    return None


def _parse_f64(s: str) -> Optional[float]:
    """serde_yaml_ng ``parse_f64`` (Rust ``f64::from_str`` grammar, finite only)."""
    if s[:1] == "+":
        unpositive = s[1:]
        if unpositive[:1] in ("+", "-"):
            return None
    else:
        unpositive = s
    if unpositive in (".inf", ".Inf", ".INF"):
        return math.inf
    if s in ("-.inf", "-.Inf", "-.INF"):
        return -math.inf
    if s in (".nan", ".NaN", ".NAN"):
        return math.nan
    if _RUST_F64.match(unpositive):
        f = float(unpositive)
        return f if math.isfinite(f) else None
    return None  # Rust parses inf/nan words, but they are not finite → None


def _parse_null(s: str) -> bool:
    return s in ("null", "Null", "NULL", "~")


def _parse_bool(s: str) -> Optional[bool]:
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    return None


def _untagged_scalar(s: str) -> Any:
    """serde_yaml_ng ``visit_untagged_scalar`` (plain scalars)."""
    if s == "" or _parse_null(s):
        return None
    b = _parse_bool(s)
    if b is not None:
        return b
    n = _parse_int(s)
    if n is not None:
        return n
    if not _digits_but_not_number(s):
        f = _parse_f64(s)
        if f is not None:
            return f
    return s


def _scalar(event: ev.ScalarEvent, tagged_already: bool) -> Any:
    """serde_yaml_ng ``visit_scalar``."""
    v: str = event.value
    tag = event.tag
    plain = event.style is None
    if tag is not None and not tagged_already:
        if tag == _TAG_BOOL:
            b = _parse_bool(v)
            if b is None:
                raise KernelYamlError("invalid value: expected a boolean")
            return b
        if tag == _TAG_INT:
            n = _parse_int(v)
            if n is None:
                raise KernelYamlError("invalid value: expected an integer")
            return n
        if tag == _TAG_FLOAT:
            f = _parse_f64(v)
            if f is None:
                raise KernelYamlError("invalid value: expected a float")
            return f
        if tag == _TAG_NULL:
            if not _parse_null(v):
                raise KernelYamlError("invalid value: expected null")
            return None
        if tag.startswith("!") and plain:
            return _untagged_scalar(v)
    elif plain:
        return _untagged_scalar(v)
    return v


def _enum_tag(tag: Optional[str]) -> Optional[str]:
    """serde_yaml_ng ``parse_tag``: local tags (``!...``) become ``Tagged``."""
    if not tag or tag[0] != "!":
        return None
    try:
        tag.encode("utf-8")
    except UnicodeEncodeError:
        return None  # not valid UTF-8 (from %-escapes): serde_yaml_ng parse_tag → None
    return tag[1:] or tag


# --- document loading --------------------------------------------------------

class _Parser(LibyamlScanner, yaml.parser.Parser):
    """PyYAML's parser over the libyaml scanner port, with libyaml's
    directive rules (``%YAML`` must be 1.1 or 1.2, no duplicates)."""

    def __init__(self, text: str) -> None:
        LibyamlScanner.__init__(self, text)
        yaml.parser.Parser.__init__(self)

    def parse_flow_sequence_entry_mapping_key(self) -> Any:
        # libyaml parse_flow_sequence_entry_mapping_key: the KEY token is
        # already consumed by parse_flow_sequence_entry; when the key is empty
        # it also consumes the next token (`:`, `,` or `]`). PyYAML does not,
        # so `[? , a]` / `[?]` parse in PyYAML and fail in the kernel.
        self.get_token()  # KEY
        if not self.check_token(yaml.tokens.ValueToken, yaml.tokens.FlowEntryToken,
                                yaml.tokens.FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        token = self.get_token()
        self.state = self.parse_flow_sequence_entry_mapping_value
        return self.process_empty_scalar(token.end_mark)

    def process_directives(self) -> Any:
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(yaml.tokens.DirectiveToken):
            token = self.get_token()
            if token.name == "YAML":
                if self.yaml_version is not None:
                    raise yaml.parser.ParserError(
                        None, None, "found duplicate %YAML directive", token.start_mark)
                if token.value not in ((1, 1), (1, 2)):
                    raise yaml.parser.ParserError(
                        None, None, "found incompatible YAML document", token.start_mark)
                self.yaml_version = token.value
            elif token.name == "TAG":
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise yaml.parser.ParserError(
                        None, None, "found duplicate %TAG directive", token.start_mark)
                self.tag_handles[handle] = prefix
        value = self.yaml_version, (self.tag_handles.copy() if self.tag_handles else None)
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value


def _events(text: str) -> List[Any]:
    """Events of the single document (serde_yaml_ng ``Loader``)."""
    try:
        parser = _Parser(text)
        stream: List[Any] = []
        while parser.check_event():
            stream.append(parser.get_event())
    except yaml.YAMLError as e:
        raise KernelYamlError(str(e)) from None
    docs: List[List[Any]] = []
    current: Optional[List[Any]] = None
    for event in stream:
        if isinstance(event, ev.DocumentStartEvent):
            current = []
        elif isinstance(event, ev.DocumentEndEvent):
            if current is not None:
                docs.append(current)
            current = None
        elif current is not None:
            current.append(event)
    if len(docs) > 1:
        raise KernelYamlError(
            "deserializing from YAML containing more than one document is not supported")
    return docs[0] if docs else []


class _Builder:
    """serde_yaml_ng ``DeserializerFromEvents`` → ``Value``.

    Anchored nodes are built once and memoised with the number of alias jumps
    and the collection depth they contain, so an alias costs O(1) while the
    jump count and depth checks come out exactly as the kernel's re-walk.
    """

    def __init__(self, events: List[Any]) -> None:
        self.events = events
        self.limit = max(len(events), 1) * _JUMP_FACTOR
        self.jumps = 0
        # alias event index -> anchored node event index (resolved at load)
        self.alias_target: Dict[int, int] = {}
        # anchored node index -> (value, jumps inside, depth inside, end index)
        self.memo: Dict[int, Tuple[Any, int, int, int]] = {}
        self.in_progress: Set[int] = set()
        self._resolve_aliases()

    def _resolve_aliases(self) -> None:
        # serde_yaml_ng Loader: an anchor gets id = len(anchors) *after* any
        # earlier definition of the same name, so a redefined name reuses a
        # slot and a later new anchor can take an id already in use. An alias
        # takes the id its name has when the alias is read; the id's target is
        # the last node registered under it anywhere in the document.
        anchors: Dict[str, int] = {}
        id_pos: Dict[int, int] = {}
        alias_id: Dict[int, int] = {}
        for i, e in enumerate(self.events):
            if isinstance(e, ev.AliasEvent):
                if e.anchor not in anchors:
                    raise KernelYamlError("unknown anchor")
                alias_id[i] = anchors[e.anchor]
            elif isinstance(e, (ev.ScalarEvent, ev.SequenceStartEvent,
                                ev.MappingStartEvent)) and e.anchor is not None:
                new_id = len(anchors)
                anchors[e.anchor] = new_id
                id_pos[new_id] = i
        self.alias_target = {i: id_pos[a] for i, a in alias_id.items()}

    def build(self) -> Any:
        if not self.events:
            return None  # Event::Void → Value::Null
        # Structural nesting past the limit fails before any recursion.
        level = 0
        for e in self.events:
            if isinstance(e, (ev.SequenceStartEvent, ev.MappingStartEvent)):
                level += 1
                if level > _MAX_DEPTH:
                    raise KernelYamlError("recursion limit exceeded")
            elif isinstance(e, (ev.SequenceEndEvent, ev.MappingEndEvent)):
                level -= 1
        value, _jumps, depth, _end = self._node(0)
        if depth > _MAX_DEPTH:
            raise KernelYamlError("recursion limit exceeded")
        if self.jumps > self.limit:
            raise KernelYamlError("repetition limit exceeded")
        return value

    def _node(self, i: int) -> Tuple[Any, int, int, int]:
        """Build the node at event ``i``.

        Returns (value, alias jumps inside, collection depth, next index).
        """
        e = self.events[i]
        if isinstance(e, ev.AliasEvent):
            value, inner_jumps, depth, _end = self._anchored(self.alias_target[i])
            self._jump(1 + inner_jumps)
            return value, 1 + inner_jumps, depth, i + 1
        if getattr(e, "anchor", None) is not None:
            value, inner_jumps, depth, end = self._anchored(i)
            self._jump(inner_jumps)  # the walk at the definition site
            return value, inner_jumps, depth, end
        return self._build(i)

    def _anchored(self, i: int) -> Tuple[Any, int, int, int]:
        """Value of the anchored node at ``i``, built once. The jump count it
        returns is charged by the caller, once per walk (definition or alias)."""
        if i in self.memo:
            return self.memo[i]
        if i in self.in_progress:
            # An alias inside its own anchor: the kernel recurses until the
            # depth or repetition limit trips.
            raise KernelYamlError("recursion limit exceeded")
        self.in_progress.add(i)
        before = self.jumps
        value, _j, depth, end = self._build(i)
        inner = self.jumps - before
        self.jumps = before
        self.in_progress.discard(i)
        result = (value, inner, depth, end)
        self.memo[i] = result
        return result

    def _jump(self, n: int) -> None:
        self.jumps += n
        if self.jumps > self.limit:
            raise KernelYamlError("repetition limit exceeded")

    def _build(self, i: int) -> Tuple[Any, int, int, int]:
        e = self.events[i]
        start_jumps = self.jumps
        if isinstance(e, ev.ScalarEvent):
            tag = _enum_tag(e.tag)
            if tag is not None:
                return Tagged(tag, _scalar(e, True)), 0, 0, i + 1
            return _scalar(e, False), 0, 0, i + 1
        if isinstance(e, ev.SequenceStartEvent):
            items: List[Any] = []
            depth = 0
            j = i + 1
            while not isinstance(self.events[j], ev.SequenceEndEvent):
                value, _jumps, d, j = self._node(j)
                items.append(value)
                depth = max(depth, d)
            depth += 1
            if depth > _MAX_DEPTH:
                raise KernelYamlError("recursion limit exceeded")
            tag = _enum_tag(e.tag)
            result: Any = Tagged(tag, items) if tag is not None else items
            return result, self.jumps - start_jumps, depth, j + 1
        if isinstance(e, ev.MappingStartEvent):
            mapping = Mapping()
            depth = 0
            j = i + 1
            while not isinstance(self.events[j], ev.MappingEndEvent):
                key, _jumps, dk, j = self._node(j)
                k = _key(key)
                if k in mapping:
                    raise KernelYamlError("duplicate entry with key")
                value, _jumps, dv, j = self._node(j)
                mapping[k] = value
                depth = max(depth, dk, dv)
            depth += 1
            if depth > _MAX_DEPTH:
                raise KernelYamlError("recursion limit exceeded")
            tag = _enum_tag(e.tag)
            result = Tagged(tag, mapping) if tag is not None else mapping
            return result, self.jumps - start_jumps, depth, j + 1
        raise KernelYamlError("unexpected event")  # pragma: no cover


def load(text: str) -> Any:
    """Load YAML exactly as faf-kernel reads it, or raise :class:`KernelYamlError`."""
    return _Builder(_events(text)).build()
