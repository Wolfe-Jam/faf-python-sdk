"""
libyaml scanner, ported for the kernel YAML loader.

faf-kernel reads YAML with serde_yaml_ng, which runs unsafe-libyaml 0.2.11 (a
Rust translation of libyaml 0.2.5). PyYAML's pure-Python scanner differs from
libyaml in whitespace and indicator handling (tabs inside plain scalars and as
separators, ``:`` in flow context, a BOM at the start of a line, tag and anchor
terminators, block-scalar indentation), and those differences decide whether a
file parses at all. This module is a line-by-line port of unsafe-libyaml's
``scanner.rs`` (plus the reader's printable check) that produces PyYAML token
objects, so PyYAML's parser can run on top of it.

Input is text (serde_yaml_ng passes UTF-8 with the encoding preset, so the
reader does not strip a BOM; the scanner skips one at column 0 of a line).
"""

import re
from collections import deque
from typing import Any, Deque, List, Optional, Tuple

from yaml import tokens as tk
from yaml.error import Mark
from yaml.scanner import ScannerError

_NON_PRINTABLE = re.compile(
    "[^\x09\x0a\x0d\x20-\x7e\x85\xa0-퟿-�\U00010000-\U0010ffff]")
_BREAKS = "\r\n\x85  "
_URI_CHARS = ";/?:@&=+$.%!~*'()"
_ESCAPES = {
    "0": "\0", "a": "\x07", "b": "\x08", "t": "\t", "\t": "\t", "n": "\n",
    "v": "\x0b", "f": "\x0c", "r": "\r", "e": "\x1b", " ": " ", '"': '"',
    "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0", "L": " ", "P": " ",
}
_HEX = frozenset("0123456789abcdefABCDEF")


def _is_alpha(ch: str) -> bool:
    return ("0" <= ch <= "9") or ("A" <= ch <= "Z") or ("a" <= ch <= "z") \
        or ch == "_" or ch == "-"


def _width(ch: str) -> int:
    o = ord(ch)
    return 1 if o < 0x80 else 2 if o < 0x800 else 3 if o < 0x10000 else 4


class _SimpleKey:
    __slots__ = ("possible", "required", "token_number", "index", "line", "column")

    def __init__(self, possible: bool, required: bool, token_number: int,
                 index: int, line: int, column: int) -> None:
        self.possible = possible
        self.required = required
        self.token_number = token_number
        self.index = index
        self.line = line
        self.column = column


class LibyamlScanner:
    """unsafe-libyaml ``yaml_parser_scan`` with PyYAML's scanner interface
    (``check_token`` / ``peek_token`` / ``get_token``)."""

    def __init__(self, text: str) -> None:
        bad = _NON_PRINTABLE.search(text)
        if bad is not None:
            raise ScannerError(None, None, "control characters are not allowed", None)
        self.buf = text
        self.n = len(text)
        self.pos = 0
        self.index = 0  # byte offset (libyaml mark.index)
        self.line = 0
        self.column = 0
        self.tokens: Deque[Any] = deque()
        self.tokens_parsed = 0
        self.token_available = False
        self.stream_start_produced = False
        self.stream_end_produced = False
        self.indent = -1
        self.indents: List[int] = []
        self.flow_level = 0
        self.simple_keys: List[_SimpleKey] = []
        self.simple_key_allowed = False

    # --- PyYAML scanner interface --------------------------------------------

    def peek_token(self) -> Any:
        if not self.token_available:
            if self.stream_end_produced:
                return None
            self._fetch_more_tokens()
        return self.tokens[0]

    def get_token(self) -> Any:
        token = self.peek_token()
        if token is None:
            return None
        self.tokens.popleft()
        self.token_available = False
        self.tokens_parsed += 1
        if isinstance(token, tk.StreamEndToken):
            self.stream_end_produced = True
        return token

    def check_token(self, *choices: Any) -> bool:
        token = self.peek_token()
        if token is None:
            return False
        return not choices or isinstance(token, choices)

    # --- buffer primitives ---------------------------------------------------

    def _ch(self, k: int = 0) -> str:
        p = self.pos + k
        return self.buf[p] if p < self.n else "\0"

    def _mark(self) -> Mark:
        return Mark("<kernel>", self.index, self.line, self.column, None, 0)

    def _error(self, context: Optional[str], problem: str) -> ScannerError:
        return ScannerError(context, None, problem, self._mark())

    def _skip(self) -> None:
        self.index += _width(self.buf[self.pos])
        self.column += 1
        self.pos += 1

    def _read(self) -> str:
        ch = self.buf[self.pos]
        self._skip()
        return ch

    def _is_blank(self, k: int = 0) -> bool:
        return self._ch(k) in " \t"

    def _is_break(self, k: int = 0) -> bool:
        return self._ch(k) in _BREAKS and self._ch(k) != "\0"

    def _is_breakz(self, k: int = 0) -> bool:
        return self._ch(k) in _BREAKS or self._ch(k) == "\0"

    def _is_blankz(self, k: int = 0) -> bool:
        return self._is_blank(k) or self._is_breakz(k)

    def _is_z(self) -> bool:
        return self.pos >= self.n

    def _skip_line(self) -> None:
        if self._ch() == "\r" and self._ch(1) == "\n":
            self.index += 2
            self.pos += 2
            self.column = 0
            self.line += 1
        elif self._is_break():
            self.index += _width(self.buf[self.pos])
            self.pos += 1
            self.column = 0
            self.line += 1

    def _read_line(self) -> str:
        ch = self._ch()
        if ch == "\r" and self._ch(1) == "\n":
            self._skip_line()
            return "\n"
        if ch in ("\r", "\n", "\x85"):
            self._skip_line()
            return "\n"
        if ch in (" ", " "):
            self._skip_line()
            return ch
        return ""

    def _doc_indicator(self) -> bool:
        return self.column == 0 and (
            (self._ch() == "-" and self._ch(1) == "-" and self._ch(2) == "-")
            or (self._ch() == "." and self._ch(1) == "." and self._ch(2) == ".")
        ) and self._is_blankz(3)

    # --- token queue ---------------------------------------------------------

    def _fetch_more_tokens(self) -> None:
        while True:
            need = False
            if not self.tokens:
                need = True
            else:
                self._stale_simple_keys()
                for sk in self.simple_keys:
                    if sk.possible and sk.token_number == self.tokens_parsed:
                        need = True
                        break
            if not need:
                break
            self._fetch_next_token()
        self.token_available = True

    def _fetch_next_token(self) -> None:
        if not self.stream_start_produced:
            self._fetch_stream_start()
            return
        self._scan_to_next_token()
        self._stale_simple_keys()
        self._unroll_indent(self.column)
        if self._is_z():
            self._fetch_stream_end()
            return
        ch = self._ch()
        if self.column == 0 and ch == "%":
            self._fetch_directive()
            return
        if self.column == 0 and ch == "-" and self._ch(1) == "-" and self._ch(2) == "-" \
                and self._is_blankz(3):
            self._fetch_document_indicator(tk.DocumentStartToken)
            return
        if self.column == 0 and ch == "." and self._ch(1) == "." and self._ch(2) == "." \
                and self._is_blankz(3):
            self._fetch_document_indicator(tk.DocumentEndToken)
            return
        if ch == "[":
            self._fetch_flow_collection_start(tk.FlowSequenceStartToken)
            return
        if ch == "{":
            self._fetch_flow_collection_start(tk.FlowMappingStartToken)
            return
        if ch == "]":
            self._fetch_flow_collection_end(tk.FlowSequenceEndToken)
            return
        if ch == "}":
            self._fetch_flow_collection_end(tk.FlowMappingEndToken)
            return
        if ch == ",":
            self._fetch_flow_entry()
            return
        if ch == "-" and self._is_blankz(1):
            self._fetch_block_entry()
            return
        if ch == "?" and (self.flow_level or self._is_blankz(1)):
            self._fetch_key()
            return
        if ch == ":" and (self.flow_level or self._is_blankz(1)):
            self._fetch_value()
            return
        if ch == "*":
            self._fetch_anchor(tk.AliasToken)
            return
        if ch == "&":
            self._fetch_anchor(tk.AnchorToken)
            return
        if ch == "!":
            self._fetch_tag()
            return
        if ch == "|" and not self.flow_level:
            self._fetch_block_scalar(True)
            return
        if ch == ">" and not self.flow_level:
            self._fetch_block_scalar(False)
            return
        if ch == "'":
            self._fetch_flow_scalar(True)
            return
        if ch == '"':
            self._fetch_flow_scalar(False)
            return
        if not (self._is_blankz() or ch in "-?:,[]{}#&*!|>'\"%@`") \
                or (ch == "-" and not self._is_blank(1)) \
                or (not self.flow_level and ch in "?:" and not self._is_blankz(1)):
            self._fetch_plain_scalar()
            return
        raise self._error("while scanning for the next token",
                          "found character that cannot start any token")

    # --- simple keys, indentation, flow level --------------------------------

    def _stale_simple_keys(self) -> None:
        for sk in self.simple_keys:
            if sk.possible and (sk.line < self.line or sk.index + 1024 < self.index):
                if sk.required:
                    raise self._error("while scanning a simple key",
                                      "could not find expected ':'")
                sk.possible = False

    def _save_simple_key(self) -> None:
        required = not self.flow_level and self.indent == self.column
        if self.simple_key_allowed:
            sk = _SimpleKey(True, required, self.tokens_parsed + len(self.tokens),
                            self.index, self.line, self.column)
            self._remove_simple_key()
            self.simple_keys[-1] = sk

    def _remove_simple_key(self) -> None:
        sk = self.simple_keys[-1]
        if sk.possible and sk.required:
            raise self._error("while scanning a simple key", "could not find expected ':'")
        sk.possible = False

    def _increase_flow_level(self) -> None:
        self.simple_keys.append(_SimpleKey(False, False, 0, 0, 0, 0))
        self.flow_level += 1
        if self.flow_level > 128:
            # More than 128 nested collections is unreadable to the kernel
            # (serde_yaml_ng recursion limit), so stop here: the simple-key
            # scan is O(flow depth) per token and would go quadratic.
            raise self._error(None, "recursion limit exceeded")

    def _decrease_flow_level(self) -> None:
        if self.flow_level:
            self.flow_level -= 1
            self.simple_keys.pop()

    def _roll_indent(self, column: int, number: int, token_cls: Any, mark: Mark) -> None:
        if self.flow_level:
            return
        if self.indent < column:
            self.indents.append(self.indent)
            if len(self.indents) > 128:
                # More than 128 nested block collections is unreadable to the
                # kernel (serde_yaml_ng recursion limit). Stop here, as for flow
                # nesting: reading on queues one BlockEnd per open level.
                raise self._error(None, "recursion limit exceeded")
            self.indent = column
            token = token_cls(mark, mark)
            if number == -1:
                self.tokens.append(token)
            else:
                self.tokens.insert(number - self.tokens_parsed, token)

    def _unroll_indent(self, column: int) -> None:
        if self.flow_level:
            return
        while self.indent > column:
            m = self._mark()
            self.tokens.append(tk.BlockEndToken(m, m))
            self.indent = self.indents.pop()

    # --- fetchers ------------------------------------------------------------

    def _fetch_stream_start(self) -> None:
        self.indent = -1
        self.simple_keys.append(_SimpleKey(False, False, 0, 0, 0, 0))
        self.simple_key_allowed = True
        self.stream_start_produced = True
        m = self._mark()
        self.tokens.append(tk.StreamStartToken(m, m, encoding="utf-8"))

    def _fetch_stream_end(self) -> None:
        if self.column != 0:
            self.column = 0
            self.line += 1
        self._unroll_indent(-1)
        self._remove_simple_key()
        self.simple_key_allowed = False
        m = self._mark()
        self.tokens.append(tk.StreamEndToken(m, m))

    def _fetch_directive(self) -> None:
        self._unroll_indent(-1)
        self._remove_simple_key()
        self.simple_key_allowed = False
        self.tokens.append(self._scan_directive())

    def _fetch_document_indicator(self, token_cls: Any) -> None:
        self._unroll_indent(-1)
        self._remove_simple_key()
        self.simple_key_allowed = False
        start = self._mark()
        self._skip()
        self._skip()
        self._skip()
        self.tokens.append(token_cls(start, self._mark()))

    def _fetch_flow_collection_start(self, token_cls: Any) -> None:
        self._save_simple_key()
        self._increase_flow_level()
        self.simple_key_allowed = True
        start = self._mark()
        self._skip()
        self.tokens.append(token_cls(start, self._mark()))

    def _fetch_flow_collection_end(self, token_cls: Any) -> None:
        self._remove_simple_key()
        self._decrease_flow_level()
        self.simple_key_allowed = False
        start = self._mark()
        self._skip()
        self.tokens.append(token_cls(start, self._mark()))

    def _fetch_flow_entry(self) -> None:
        self._remove_simple_key()
        self.simple_key_allowed = True
        start = self._mark()
        self._skip()
        self.tokens.append(tk.FlowEntryToken(start, self._mark()))

    def _fetch_block_entry(self) -> None:
        if not self.flow_level:
            if not self.simple_key_allowed:
                raise self._error(None, "block sequence entries are not allowed in this context")
            self._roll_indent(self.column, -1, tk.BlockSequenceStartToken, self._mark())
        self._remove_simple_key()
        self.simple_key_allowed = True
        start = self._mark()
        self._skip()
        self.tokens.append(tk.BlockEntryToken(start, self._mark()))

    def _fetch_key(self) -> None:
        if not self.flow_level:
            if not self.simple_key_allowed:
                raise self._error(None, "mapping keys are not allowed in this context")
            self._roll_indent(self.column, -1, tk.BlockMappingStartToken, self._mark())
        self._remove_simple_key()
        self.simple_key_allowed = not self.flow_level
        start = self._mark()
        self._skip()
        self.tokens.append(tk.KeyToken(start, self._mark()))

    def _fetch_value(self) -> None:
        sk = self.simple_keys[-1]
        if sk.possible:
            m = Mark("<kernel>", sk.index, sk.line, sk.column, None, 0)
            self.tokens.insert(sk.token_number - self.tokens_parsed, tk.KeyToken(m, m))
            self._roll_indent(sk.column, sk.token_number, tk.BlockMappingStartToken, m)
            sk.possible = False
            self.simple_key_allowed = False
        else:
            if not self.flow_level:
                if not self.simple_key_allowed:
                    raise self._error(None, "mapping values are not allowed in this context")
                self._roll_indent(self.column, -1, tk.BlockMappingStartToken, self._mark())
            self.simple_key_allowed = not self.flow_level
        start = self._mark()
        self._skip()
        self.tokens.append(tk.ValueToken(start, self._mark()))

    def _fetch_anchor(self, token_cls: Any) -> None:
        self._save_simple_key()
        self.simple_key_allowed = False
        self.tokens.append(self._scan_anchor(token_cls))

    def _fetch_tag(self) -> None:
        self._save_simple_key()
        self.simple_key_allowed = False
        self.tokens.append(self._scan_tag())

    def _fetch_block_scalar(self, literal: bool) -> None:
        self._remove_simple_key()
        self.simple_key_allowed = True
        self.tokens.append(self._scan_block_scalar(literal))

    def _fetch_flow_scalar(self, single: bool) -> None:
        self._save_simple_key()
        self.simple_key_allowed = False
        self.tokens.append(self._scan_flow_scalar(single))

    def _fetch_plain_scalar(self) -> None:
        self._save_simple_key()
        self.simple_key_allowed = False
        self.tokens.append(self._scan_plain_scalar())

    # --- scanners ------------------------------------------------------------

    def _scan_to_next_token(self) -> None:
        while True:
            if self.column == 0 and self._ch() == "﻿":
                self._skip()
            while self._ch() == " " or (
                    (self.flow_level or not self.simple_key_allowed) and self._ch() == "\t"):
                self._skip()
            if self._ch() == "#":
                while not self._is_breakz():
                    self._skip()
            if not self._is_break():
                break
            self._skip_line()
            if not self.flow_level:
                self.simple_key_allowed = True

    def _scan_directive(self) -> Any:
        start = self._mark()
        self._skip()
        name = ""
        while _is_alpha(self._ch()):
            name += self._read()
        if not name:
            raise self._error("while scanning a directive",
                              "could not find expected directive name")
        if not self._is_blankz():
            raise self._error("while scanning a directive",
                              "found unexpected non-alphabetical character")
        value: Tuple[Any, Any]
        if name == "YAML":
            while self._is_blank():
                self._skip()
            major = self._scan_version_number()
            if self._ch() != ".":
                raise self._error("while scanning a %YAML directive",
                                  "did not find expected digit or '.' character")
            self._skip()
            minor = self._scan_version_number()
            value = (major, minor)
        elif name == "TAG":
            while self._is_blank():
                self._skip()
            handle = self._scan_tag_handle(True)
            if not self._is_blank():
                raise self._error("while scanning a %TAG directive",
                                  "did not find expected whitespace")
            while self._is_blank():
                self._skip()
            prefix = self._scan_tag_uri(True, True, None)
            if not self._is_blankz():
                raise self._error("while scanning a %TAG directive",
                                  "did not find expected whitespace or line break")
            value = (handle, prefix)
        else:
            raise self._error("while scanning a directive", "found unknown directive name")
        end = self._mark()
        while self._is_blank():
            self._skip()
        if self._ch() == "#":
            while not self._is_breakz():
                self._skip()
        if not self._is_breakz():
            raise self._error("while scanning a directive",
                              "did not find expected comment or line break")
        if self._is_break():
            self._skip_line()
        return tk.DirectiveToken(name, value, start, end)

    def _scan_version_number(self) -> int:
        value = 0
        length = 0
        while "0" <= self._ch() <= "9":
            length += 1
            if length > 9:
                raise self._error("while scanning a %YAML directive",
                                  "found extremely long version number")
            value = value * 10 + int(self._ch())
            self._skip()
        if length == 0:
            raise self._error("while scanning a %YAML directive",
                              "did not find expected version number")
        return value

    def _scan_anchor(self, token_cls: Any) -> Any:
        start = self._mark()
        self._skip()
        value = ""
        while _is_alpha(self._ch()):
            value += self._read()
        if not value or not (self._is_blankz() or self._ch() in "?:,]}%@`"):
            raise self._error(
                "while scanning an anchor" if token_cls is tk.AnchorToken
                else "while scanning an alias",
                "did not find expected alphabetic or numeric character")
        return token_cls(value, start, self._mark())

    def _scan_tag(self) -> Any:
        start = self._mark()
        handle: str
        if self._ch(1) == "<":
            handle = ""
            self._skip()
            self._skip()
            suffix = self._scan_tag_uri(True, False, None)
            if self._ch() != ">":
                raise self._error("while scanning a tag", "did not find the expected '>'")
            self._skip()
        else:
            handle = self._scan_tag_handle(False)
            if handle[0] == "!" and len(handle) > 1 and handle[-1] == "!":
                suffix = self._scan_tag_uri(False, False, None)
            else:
                suffix = self._scan_tag_uri(False, False, handle)
                handle = "!"
                if suffix == "":
                    handle, suffix = suffix, handle
        if not self._is_blankz():
            if not self.flow_level or self._ch() != ",":
                raise self._error("while scanning a tag",
                                  "did not find expected whitespace or line break")
        return tk.TagToken((handle or None, suffix), start, self._mark())

    def _scan_tag_handle(self, directive: bool) -> str:
        if self._ch() != "!":
            raise self._error(
                "while scanning a tag directive" if directive else "while scanning a tag",
                "did not find expected '!'")
        string = self._read()
        while _is_alpha(self._ch()):
            string += self._read()
        if self._ch() == "!":
            string += self._read()
        elif directive and string != "!":
            raise self._error("while parsing a tag directive", "did not find expected '!'")
        return string

    def _scan_tag_uri(self, uri_char: bool, directive: bool, head: Optional[str]) -> str:
        length = len(head) if head else 0
        string = head[1:] if head and length > 1 else ""
        while True:
            ch = self._ch()
            if not (_is_alpha(ch) or (ch in _URI_CHARS and ch != "\0")
                    or (uri_char and ch in ",[]" and ch != "\0")):
                break
            if ch == "%":
                string += self._scan_uri_escapes(directive)
            else:
                string += self._read()
            length += 1
        if length == 0:
            raise self._error(
                "while parsing a %TAG directive" if directive else "while parsing a tag",
                "did not find expected tag URI")
        return string

    def _scan_uri_escapes(self, directive: bool) -> str:
        context = "while parsing a %TAG directive" if directive else "while parsing a tag"
        octets = bytearray()
        width = 0
        while True:
            if not (self._ch() == "%" and self._ch(1) in _HEX and self._ch(2) in _HEX):
                raise self._error(context, "did not find URI escaped octet")
            octet = int(self._ch(1) + self._ch(2), 16)
            if width == 0:
                width = 1 if octet & 0x80 == 0 else 2 if octet & 0xE0 == 0xC0 \
                    else 3 if octet & 0xF0 == 0xE0 else 4 if octet & 0xF8 == 0xF0 else 0
                if width == 0:
                    raise self._error(context, "found an incorrect leading UTF-8 octet")
            elif octet & 0xC0 != 0x80:
                raise self._error(context, "found an incorrect trailing UTF-8 octet")
            octets.append(octet)
            self._skip()
            self._skip()
            self._skip()
            width -= 1
            if width == 0:
                break
        return octets.decode("utf-8", errors="surrogateescape")

    def _scan_block_scalar(self, literal: bool) -> Any:
        start = self._mark()
        self._skip()
        chomping = 0
        increment = 0
        if self._ch() in "+-" and self._ch() != "\0":
            chomping = 1 if self._ch() == "+" else -1
            self._skip()
            if "0" <= self._ch() <= "9":
                if self._ch() == "0":
                    raise self._error("while scanning a block scalar",
                                      "found an indentation indicator equal to 0")
                increment = int(self._ch())
                self._skip()
        elif "0" <= self._ch() <= "9":
            if self._ch() == "0":
                raise self._error("while scanning a block scalar",
                                  "found an indentation indicator equal to 0")
            increment = int(self._ch())
            self._skip()
            if self._ch() in "+-" and self._ch() != "\0":
                chomping = 1 if self._ch() == "+" else -1
                self._skip()
        while self._is_blank():
            self._skip()
        if self._ch() == "#":
            while not self._is_breakz():
                self._skip()
        if not self._is_breakz():
            raise self._error("while scanning a block scalar",
                              "did not find expected comment or line break")
        if self._is_break():
            self._skip_line()
        indent = 0
        if increment:
            indent = self.indent + increment if self.indent >= 0 else increment
        string = ""
        leading_break = ""
        leading_blank = False
        indent, trailing_breaks = self._scan_block_scalar_breaks(indent, "")
        while self.column == indent and not self._is_z():
            trailing_blank = self._is_blank()
            if not literal and leading_break[:1] == "\n" and not leading_blank \
                    and not trailing_blank:
                if trailing_breaks == "":
                    string += " "
                leading_break = ""
            else:
                string += leading_break
                leading_break = ""
            string += trailing_breaks
            trailing_breaks = ""
            leading_blank = self._is_blank()
            while not self._is_breakz():
                string += self._read()
            leading_break = self._read_line()
            indent, trailing_breaks = self._scan_block_scalar_breaks(indent, trailing_breaks)
        if chomping != -1:
            string += leading_break
        if chomping == 1:
            string += trailing_breaks
        return tk.ScalarToken(string, False, start, self._mark(), "|" if literal else ">")

    def _scan_block_scalar_breaks(self, indent: int, breaks: str) -> Tuple[int, str]:
        max_indent = 0
        while True:
            while (indent == 0 or self.column < indent) and self._ch() == " ":
                self._skip()
            if self.column > max_indent:
                max_indent = self.column
            if (indent == 0 or self.column < indent) and self._ch() == "\t":
                raise self._error("while scanning a block scalar",
                                  "found a tab character where an indentation space is expected")
            if not self._is_break():
                break
            breaks += self._read_line()
        if indent == 0:
            indent = max(max_indent, self.indent + 1, 1)
        return indent, breaks

    def _scan_flow_scalar(self, single: bool) -> Any:
        start = self._mark()
        quote = "'" if single else '"'
        self._skip()
        string = ""
        leading_break = ""
        trailing_breaks = ""
        whitespaces = ""
        while True:
            if self._doc_indicator():
                raise self._error("while scanning a quoted scalar",
                                  "found unexpected document indicator")
            if self._is_z():
                raise self._error("while scanning a quoted scalar",
                                  "found unexpected end of stream")
            leading_blanks = False
            while not self._is_blankz():
                ch = self._ch()
                if single and ch == "'" and self._ch(1) == "'":
                    string += "'"
                    self._skip()
                    self._skip()
                    continue
                if ch == quote:
                    break
                if not single and ch == "\\" and self._is_break(1):
                    self._skip()
                    self._skip_line()
                    leading_blanks = True
                    break
                if not single and ch == "\\":
                    esc = self._ch(1)
                    code_length = 0
                    if esc in _ESCAPES and esc != "\0":
                        string += _ESCAPES[esc]
                    elif esc == "x":
                        code_length = 2
                    elif esc == "u":
                        code_length = 4
                    elif esc == "U":
                        code_length = 8
                    else:
                        raise self._error("while parsing a quoted scalar",
                                          "found unknown escape character")
                    self._skip()
                    self._skip()
                    if code_length:
                        value = 0
                        for k in range(code_length):
                            if self._ch(k) not in _HEX:
                                raise self._error("while parsing a quoted scalar",
                                                  "did not find expected hexadecimal number")
                            value = (value << 4) + int(self._ch(k), 16)
                        if 0xD800 <= value <= 0xDFFF or value > 0x10FFFF:
                            raise self._error("while parsing a quoted scalar",
                                              "found invalid Unicode character escape code")
                        string += chr(value)
                        for _ in range(code_length):
                            self._skip()
                    continue
                string += self._read()
            if self._ch() == quote:
                break
            while self._is_blank() or self._is_break():
                if self._is_blank():
                    if not leading_blanks:
                        whitespaces += self._read()
                    else:
                        self._skip()
                elif not leading_blanks:
                    whitespaces = ""
                    leading_break = self._read_line()
                    leading_blanks = True
                else:
                    trailing_breaks += self._read_line()
            if leading_blanks:
                if leading_break[:1] == "\n":
                    if trailing_breaks == "":
                        string += " "
                    else:
                        string += trailing_breaks
                        trailing_breaks = ""
                    leading_break = ""
                else:
                    string += leading_break + trailing_breaks
                    leading_break = ""
                    trailing_breaks = ""
            else:
                string += whitespaces
                whitespaces = ""
        self._skip()
        return tk.ScalarToken(string, False, start, self._mark(), quote)

    def _scan_plain_scalar(self) -> Any:
        start = self._mark()
        end = start
        string = ""
        leading_break = ""
        trailing_breaks = ""
        whitespaces = ""
        leading_blanks = False
        indent = self.indent + 1
        while True:
            if self._doc_indicator():
                break
            if self._ch() == "#":
                break
            while not self._is_blankz():
                ch = self._ch()
                if self.flow_level and ch == ":" and self._ch(1) in ",?[]{}" \
                        and self._ch(1) != "\0":
                    raise self._error("while scanning a plain scalar", "found unexpected ':'")
                if (ch == ":" and self._is_blankz(1)) or (self.flow_level and ch in ",[]{}"):
                    break
                if leading_blanks or whitespaces:
                    if leading_blanks:
                        if leading_break[:1] == "\n":
                            if trailing_breaks == "":
                                string += " "
                            else:
                                string += trailing_breaks
                                trailing_breaks = ""
                            leading_break = ""
                        else:
                            string += leading_break + trailing_breaks
                            leading_break = ""
                            trailing_breaks = ""
                        leading_blanks = False
                    else:
                        string += whitespaces
                        whitespaces = ""
                string += self._read()
                end = self._mark()
            if not (self._is_blank() or self._is_break()):
                break
            while self._is_blank() or self._is_break():
                if self._is_blank():
                    if leading_blanks and self.column < indent and self._ch() == "\t":
                        raise self._error("while scanning a plain scalar",
                                          "found a tab character that violates indentation")
                    if not leading_blanks:
                        whitespaces += self._read()
                    else:
                        self._skip()
                elif not leading_blanks:
                    whitespaces = ""
                    leading_break = self._read_line()
                    leading_blanks = True
                else:
                    trailing_breaks += self._read_line()
            if not self.flow_level and self.column < indent:
                break
        if leading_blanks:
            self.simple_key_allowed = True
        return tk.ScalarToken(string, True, start, end)
