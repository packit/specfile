# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import argparse
import re
import shlex
from typing import Tuple

from specfile.exceptions import UnterminatedMacroException
from specfile.value_parser import (
    ConditionalMacroExpansion,
    EnclosedMacroSubstitution,
    ExpressionExpansion,
    MacroSubstitution,
    ShellExpansion,
    SingleArgEnclosedMacroSubstitution,
    ValueParser,
)

_RE_SUBSTR = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;'
    r'\s*echo\s+["\']?\$\{\1:(\d+)(?::(%\{?\w+\}?|\d+))?\}["\']?\s*$'
)
_RE_BASH_REPLACE = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;'
    r'\s*echo\s+["\']?\$\{\1(//?)([^/}]*)/([^}]*)\}["\']?$'
)
_RE_BASH_LOWER = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*echo\s+["\']?\$\{\1,,\}["\']?$'
)
_RE_BASH_UPPER = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*echo\s+["\']?\$\{\1\^\^\}["\']?$'
)
_RE_PIPE = re.compile(r"^echo\s+(.+?)\|\s*(.+)$", re.DOTALL)
_RE_HERESTRING = re.compile(r"^(.+?)<<<\s*(.+)$", re.DOTALL)
_RE_ECHO_CONCAT = re.compile(r"^echo\s+(%\{?\w+\}?)\s+([^|].*)$")
_RE_TR_LOWER = re.compile(r"tr\s+['\"]?\[:upper:\]['\"]?\s+['\"]?\[:lower:\]['\"]?$")
_RE_TR_UPPER = re.compile(r"tr\s+['\"]?\[:lower:\]['\"]?\s+['\"]?\[:upper:\]['\"]?$")
_RE_TR_DELETE = re.compile(r"tr\s+(?:--\s+)?-d\s+[\"'](.+?)[\"']$")
_RE_TR_DELETE_BARE = re.compile(r"tr\s+(?:--\s+)?-d\s+(\S)$")
_RE_TR_REPLACE = re.compile(r"tr\s+(?:--\s+)?['\"]?(.)['\"]?\s+['\"]?(.)['\"]?$")
_RE_AWK_F = re.compile(r"awk\s+-F['\"]?(.)['\"]?\s+['\"]?\{print\s+(.+)\}['\"]?$")
_RE_AWK_FIELDS = re.compile(r'\$(\d+)|"([^"]*)"')
_RE_CUT_FIELD = re.compile(r"(\d+)?-(\d+)$")
_RE_CUT_SINGLE = re.compile(r"(\d+)$")
_RE_CUT_BYTES_VAL = re.compile(r"^(%\{?\w+\}?|\d+)$")
_RE_PRINTF_TRUNC = re.compile(
    r"""^\s*printf\s+['"]?%%?\.(\d+)s['"]?\s+['"]?(%\{?\w+\}?)['"]?\s*$"""
)
_RE_PRINTF_FLOAT = re.compile(
    r"""^\s*(?:(?:LC_ALL|LANG)=\S+[;\s]+\s*)?"""
    r"""printf\s+['"]%%?\.(\d+)f['"]?\s+['"]?(%\{?\w+\}?)['"]?\s*$"""
)
_RE_BASH_ARRAY_FIELD = re.compile(
    r"^(\w+)\s*=\s*[\"']?(%\{?\w+\}?)[\"']?\s*;\s*"
    r"(\w+)=\(\$\{\1//(.)/ \}\)\s*;\s*"
    r"echo\s+\$\{\3\[(\d+)\]\}\s*$"
)
_RE_VAR_PIPE = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*'
    r'echo\s+["\']?\$\{?\1\}?["\']?\s*\|\s*(.+)$',
    re.DOTALL,
)
_RE_VAR_HERESTRING = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*'
    r'(.+?)<<<\s*["\']?\$\{?\1\}?["\']?\s*$',
    re.DOTALL,
)
_RE_BASH_SUFFIX = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*'
    r'echo\s+["\']?\$\{\1(%%%%|%%|%)([^}]+)\}["\']?\s*$'
)
_RE_BASH_PREFIX = re.compile(
    r'^(\w+)\s*=\s*["\']?(%\{?\w+\}?)["\']?\s*;\s*'
    r'echo\s+["\']?\$\{\1(##|#)([^}]+)\}["\']?\s*$'
)
_RE_DATE_SIMPLE = re.compile(r"^\s*date\s+(?:-u\s+)?\+[\"']?([^\"']+?)[\"']?\s*$")
_RE_DATE_UTC = re.compile(r"^\s*date\s+-u\s+")
_RE_ARITHMETIC = re.compile(r"^\s*echo\s+\$\(\((.+)\)\)\s*$")
_RE_BASENAME = re.compile(r"^\s*basename\s+(%\{\w+\}|%\w+)\s*$")
_RE_DIRNAME = re.compile(r"^\s*dirname\s+(%\{\w+\}|%\w+)\s*$")
_RE_TEST_STR = re.compile(
    r"""^\s*test\s+["']?(.+?)["']?\s+(!=|==|=)\s+["']?(.+?)["']?"""
    r"""\s*&&\s*echo\s+["']?(.+?)["']?\s*\|\|\s*echo\s+["']?(.+?)["']?\s*$"""
)
_RE_TEST_EMPTY = re.compile(
    r"""^\s*\[\s+-z\s+["']?(.+?)["']?\s*\]"""
    r"""\s*&&\s*echo\s+["']?(.+?)["']?\s*\|\|\s*echo\s+["']?(.+?)["']?\s*$"""
)

_LUA_STRING_LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')


def _strip_lua_comments(code):
    """Strip Lua comments while preserving string literals.

    Processes code left-to-right so that ``--`` inside a quoted string
    is never mistaken for a comment start.
    """
    result = []
    i = 0
    while i < len(code):
        if code[i] in ('"', "'"):
            quote = code[i]
            result.append(code[i])
            i += 1
            while i < len(code) and code[i] != quote:
                if code[i] == "\\" and i + 1 < len(code):
                    result.append(code[i : i + 2])
                    i += 2
                else:
                    result.append(code[i])
                    i += 1
            if i < len(code):
                result.append(code[i])
                i += 1
        elif code[i : i + 2] == "--":
            j = i + 2
            if j < len(code) and code[j] == "[":
                level = 0
                k = j + 1
                while k < len(code) and code[k] == "=":
                    level += 1
                    k += 1
                if k < len(code) and code[k] == "[":
                    close = "]" + "=" * level + "]"
                    end = code.find(close, k + 1)
                    if end != -1:
                        i = end + len(close)
                    else:
                        i = len(code)
                    result.append(" ")
                    continue
            end = code.find("\n", i)
            if end != -1:
                result.append(" ")
                i = end
            else:
                result.append(" ")
                i = len(code)
        else:
            result.append(code[i])
            i += 1
    return "".join(result)


_UNSAFE_LUA_BRACKET_RE = re.compile(r"\[\s*(?![#\d])")

_UNSAFE_LUA_STRING_CONTENT_RE = re.compile(
    r"%\(|%\[|%\{(?:lua|load|include|uncompress|expand|define|global|undefine)\s*:"
    r"|%(?:load|include|define|global|undefine)\s"
)

_EXPRESSION_LUA_PREFIX_RE = re.compile(r"lua\s*:")


def _decode_lua_escapes(s):
    """Decode all Lua string escape sequences to their character values."""
    _SIMPLE = {
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
        '"': '"',
        "'": "'",
    }
    result = []
    i = 0
    while i < len(s):
        if s[i] != "\\" or i + 1 >= len(s):
            result.append(s[i])
            i += 1
            continue
        c = s[i + 1]
        if c in _SIMPLE:
            result.append(_SIMPLE[c])
            i += 2
        elif c == "z":
            i += 2
            while i < len(s) and s[i] in " \t\n\r":
                i += 1
        elif c == "x" and i + 3 < len(s):
            try:
                result.append(chr(int(s[i + 2 : i + 4], 16)))
                i += 4
            except ValueError:
                result.append(s[i])
                i += 1
        elif c == "u" and i + 2 < len(s) and s[i + 2] == "{":
            end = s.find("}", i + 3)
            if end != -1:
                try:
                    result.append(chr(int(s[i + 3 : end], 16)))
                    i = end + 1
                except (ValueError, OverflowError):
                    result.append(s[i])
                    i += 1
            else:
                result.append(s[i])
                i += 1
        elif c.isdigit():
            j = i + 1
            while j < len(s) and j < i + 4 and s[j].isdigit():
                j += 1
            num = int(s[i + 1 : j])
            result.append(chr(num % 256))
            i = j
        else:
            result.append(s[i])
            i += 1
    return "".join(result)


_UNSAFE_LUA_IDENTIFIERS = frozenset(
    {
        "_G",
        "_ENV",
        "rawget",
        "rawset",
        "rawequal",
        "getfenv",
        "setfenv",
        "getmetatable",
        "setmetatable",
        "debug",
        "package",
        "require",
        "module",
        "load",
        "loadstring",
        "loadfile",
        "dofile",
        "io",
        "collectgarbage",
        "newproxy",
        "coroutine",
        "pcall",
        "xpcall",
        "os",
        "rpm",
        "string",
    }
)

_SAFE_LUA_DOTTED_MODULES = frozenset({"string", "table", "math"})

_SAFE_LUA_DOTTED = frozenset(
    {
        "rpm.expand",
        "os.date",
        "os.clock",
        "os.time",
        "os.difftime",
    }
)

_LUA_DOTTED_RE = re.compile(r"\b([a-zA-Z_]\w*)\s*\.\s*([a-zA-Z_]\w*)")
_LUA_COLON_UNSAFE_METHOD_RE = re.compile(r":\s*(dump|char|sub|find|reverse|rep)\s*\(")
_LUA_IDENT_RE = re.compile(r"\b([a-zA-Z_]\w*)\b")

_FORMAT_CALL_RE = re.compile(r"(?:\bstring\s*\.\s*format|:\s*format)\s*\(")
_FORMAT_LITERAL_ARG_RE = re.compile(r'\s*"([^"\\]*(?:\\.[^"\\]*)*)"')
_SAFE_FORMAT_SPEC_RE = re.compile(r"%%|%[-+ #0]*\d*\.?\d*[diouxXeEfgG]")

_RPM_EXPAND_REF_RE = re.compile(r"\brpm\s*\.\s*expand\b")
_RPM_EXPAND_SAFE_CALL_RE = re.compile(r'\s*\(\s*""\s*\)')


_UNESCAPED_NEWLINE_RE = re.compile(r"(?<!\\)\n")

_CUT_PARSER = argparse.ArgumentParser(add_help=False)
_CUT_PARSER.add_argument("-d", default=None)
_CUT_PARSER.add_argument("-f", default=None)
_CUT_PARSER.add_argument("-c", default=None)
_CUT_PARSER.add_argument("-b", default=None)


class Sanitizer:
    @staticmethod
    def sanitize_shell_expansion(body: str) -> str:
        """
        Sanitize a shell expansion body. Replaces commonly used patterns with builtin macros
        or Lua expressions. Covered patterns are:

        - Substring extraction:
            `%(c=%{commit}; echo ${c:0:7})` → `%{sub %{commit}, 1, 7}`
        - Bash string replacement:
            `%(v=%{version}; echo ${v//./_})` → `%{lua:
               print((rpm.expand("%{version}"):gsub("%.", "_")))}`
        - Case conversion:
            `%(v=%{name}; echo ${v,,})` → `%{lower:%{name}}`
        - Suffix removal:
            `%(v=%{version}; echo ${v%%%%.*})` → `%{lua:
               local v=rpm.expand("%{version}")
               print(v:match("^(.-)%.") or v)}`
        - Prefix removal:
            `%(v=%{version}; echo ${v##*.})` → `%{lua:
               local v=rpm.expand("%{version}")
               print(v:match(".*%.(.*)") or v)}`
        - Pipe to tr:
            `%(echo %{name} | tr [:upper:] [:lower:])` → `%{lower:%{name}}`
        - Pipe to sed:
            `%(echo %{version} | sed 's/\\./-/g')` → `%{lua:
               print((rpm.expand("%{version}"):gsub("%.", "-")))}`
        - Pipe to awk:
            `%(echo %{version} | awk -F. '{print $1}')` → `%{lua:
               local v=rpm.expand("%{version}") local t={}
               for f in v:gmatch("[^%.]+") do t[#t+1]=f end
               print(t[1])}`
        - Pipe to cut:
            `%(echo %{version} | cut -d. -f3)` → `%{lua:
               local v=rpm.expand("%{version}") local i=0
               for f in v:gmatch("[^%.]+") do i=i+1
               if i==3 then print(f) break end end}`
        - Herestring variants of the above:
            `%(cut -d. -f3 <<< %{version})` → same as above
        - Bash array field extraction:
            `%(v=%{version}; a=(${v//./ }); echo ${a[2]})` → same as above
        - Date formatting:
            `%(date +"%Y%m%d")` → `%{lua:print(os.date("%Y%m%d"))}`
        - Arithmetic:
            `%(echo $((%{__isa_bits}+2)))` → `%[%{__isa_bits}+2]`
        - Basename / dirname:
            `%(basename %{_python3_include})` → `%{lua:
               print((rpm.expand("%{_python3_include}"):match("[^/]+$")))}`
        - String comparison:
            `%(test "%{_libdir}" != "%{_prefix}/lib" && echo 1 || echo 0)` → `%{lua:
               print(rpm.expand("%{_libdir}") ~= rpm.expand("%{_prefix}/lib") and "1" or "0")}`
        - Printf truncation:
            `%(printf %%.7s %commit)` → `%{sub %{commit}, 1, 7}`
        - Printf float formatting:
            `%(LANG=C printf "%.4f" %{cpan_ver})` → `%{lua:
               print(string.format("%%.4f", tonumber(rpm.expand("%{cpan_ver}"))))}`
        - Simple echo concatenation:
            `%(echo %{version} -beta)` → `%{version} -beta`

        Args:
            body: Shell expansion body to sanitize.

        Returns:
            Sanitized shell expansion body, or %{nil} if sanitization is not possible.
        """

        def strip_quotes(s):
            s = s.strip()
            if len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0]:
                return s[1:-1]
            return s

        def normalize_macro(expr):
            expr = strip_quotes(expr.strip())
            if expr.startswith("%") and not expr.startswith("%{"):
                expr = "%{" + expr[1:] + "}"
            if not re.match(r"^%\{\w+\}$", expr):
                return None
            return expr

        def is_safe_for_expand(s):
            return not re.search(r"%(\{\w+[\s:]|\(|\[)", s)

        def lua_pattern_escape(s):
            return "".join(f"%{c}" if c in ".+-*?()[]^$%" else c for c in s)

        def lua_string_escape(s):
            s = s.replace("\\", "\\\\")
            s = s.replace('"', '\\"')
            s = s.replace("\0", "\\0")
            s = s.replace("\a", "\\a")
            s = s.replace("\b", "\\b")
            s = s.replace("\f", "\\f")
            s = s.replace("\n", "\\n")
            s = s.replace("\r", "\\r")
            s = s.replace("\t", "\\t")
            s = s.replace("\v", "\\v")
            return s

        def sed_pattern_to_lua(s):
            _SED_C_ESCAPES = {"n": "\n", "t": "\t", "a": "\a"}
            result = []
            i = 0
            while i < len(s):
                if s[i] == "\\" and i + 1 < len(s):
                    c = s[i + 1]
                    if c in _SED_C_ESCAPES:
                        result.append(_SED_C_ESCAPES[c])
                    else:
                        result.append(f"%{c}")
                    i += 2
                elif s[i] in "%+?()":
                    result.append(f"%{s[i]}")
                    i += 1
                else:
                    result.append(s[i])
                    i += 1
            return "".join(result)

        def lua_gsub_repl_escape(s):
            """Escape ``%`` in gsub replacement strings.

            In Lua's ``string.gsub``, ``%`` is magic in the replacement
            (``%1`` = capture, ``%%`` = literal ``%``).
            """
            return s.replace("%", "%%")

        def build_lua_gsub(expr, pattern, repl, count=None):
            count_arg = f", {count}" if count is not None else ""
            esc_repl = lua_string_escape(lua_gsub_repl_escape(repl))
            return (
                f'%{{lua:print((rpm.expand("{lua_string_escape(expr)}")'
                f':gsub("{lua_string_escape(pattern)}"'
                f', "{esc_repl}"{count_arg})))}}'
            )

        def build_lua_field(expr, delim, field):
            esc = lua_string_escape(lua_pattern_escape(delim))
            return (
                f'%{{lua:local v=rpm.expand("{lua_string_escape(expr)}") '
                f"local i=0 "
                f'for f in v:gmatch("[^{esc}]+") do '
                f"i=i+1 if i=={field} then print(f) break end "
                f"end}}"
            )

        def build_lua_field_range(expr, delim, start, stop):
            esc = lua_string_escape(lua_pattern_escape(delim))
            return (
                f'%{{lua:local v=rpm.expand("{lua_string_escape(expr)}") '
                f"local t={{}} "
                f'for f in v:gmatch("[^{esc}]+") do t[#t+1]=f end '
                f'print(table.concat(t,"{lua_string_escape(delim)}",{start},{stop}))}}'
            )

        def parse_sed_substs(cmd):
            results = []
            i = 0
            while i < len(cmd):
                if (
                    cmd[i] == "s"
                    and i + 1 < len(cmd)
                    and not cmd[i + 1].isalnum()
                    and cmd[i + 1] not in " \t"
                ):
                    if i > 0 and (cmd[i - 1].isalnum() or cmd[i - 1] == "_"):
                        i += 1
                        continue
                    delim = cmd[i + 1]
                    j = i + 2
                    parts = []
                    current = []
                    while j < len(cmd) and len(parts) < 2:
                        if cmd[j] == "\\" and j + 1 < len(cmd):
                            current.append(cmd[j : j + 2])
                            j += 2
                        elif cmd[j] == delim:
                            parts.append("".join(current))
                            current = []
                            j += 1
                        else:
                            current.append(cmd[j])
                            j += 1
                    if len(parts) == 2:
                        flags = []
                        while j < len(cmd) and cmd[j].isalpha():
                            flags.append(cmd[j])
                            j += 1
                        is_global = "g" in "".join(flags)
                        results.append((parts[0], parts[1], is_global))
                        i = j
                    else:
                        i += 1
                else:
                    i += 1
            return results if results else None

        def parse_cut(cmd):
            """Parse a cut command. Returns (mode, start, end, delim) or None."""
            try:
                tokens = shlex.split(cmd)
            except ValueError:
                return None
            if not tokens or tokens[0] != "cut":
                return None
            try:
                parsed, _ = _CUT_PARSER.parse_known_args(tokens[1:])
            except (argparse.ArgumentError, SystemExit):
                return None

            byte_spec = parsed.c or parsed.b
            if byte_spec:
                if "-" in byte_spec:
                    left, right = byte_spec.split("-", 1)
                    s = left if left else "1"
                    e = right if right else None
                else:
                    s = e = byte_spec
                if _RE_CUT_BYTES_VAL.match(s) and (
                    e is None or _RE_CUT_BYTES_VAL.match(e)
                ):
                    return ("bytes", s, e, None)
                return None

            if parsed.d and parsed.f:
                m2 = _RE_CUT_FIELD.match(parsed.f)
                if m2:
                    s = int(m2.group(1)) if m2.group(1) else 1
                    return ("range", s, int(m2.group(2)), parsed.d)
                m2 = _RE_CUT_SINGLE.match(parsed.f)
                if m2:
                    n = int(m2.group(1))
                    return ("field", n, n, parsed.d)

            return None

        def build_lua_char_class(chars):
            """Build a Lua pattern character class matching any of the given chars."""
            ordered = ""
            if "]" in chars:
                ordered += "]"
                chars = chars.replace("]", "")
            chars = chars.replace("%", "%%")
            if "^" in chars:
                chars = chars.replace("^", "")
                ordered += chars + "^"
            else:
                ordered += chars
            if "-" in ordered and len(ordered) > 1:
                ordered = ordered.replace("-", "") + "-"
            return f"[{ordered}]"

        def convert_string_op(expr, cmd):
            # -- cut --
            cut = parse_cut(cmd)
            if cut:
                mode, start, end, delim = cut
                if mode == "bytes":
                    if end is not None:
                        return f"%{{sub {expr}, {start}, {end}}}"
                    return f"%{{sub {expr}, {start}}}"
                elif mode == "field":
                    return build_lua_field(expr, delim, start)
                elif mode == "range":
                    return build_lua_field_range(expr, delim, start, end)

            # -- tr case conversion --
            if _RE_TR_LOWER.match(cmd):
                return f"%{{lower:{expr}}}"
            if _RE_TR_UPPER.match(cmd):
                return f"%{{upper:{expr}}}"

            # -- tr -d (quoted multi-char or bare single-char) --
            m = _RE_TR_DELETE.match(cmd)
            if m:
                chars = m.group(1)
                if len(chars) == 1:
                    return build_lua_gsub(expr, lua_pattern_escape(chars), "")
                return build_lua_gsub(expr, build_lua_char_class(chars), "")
            m = _RE_TR_DELETE_BARE.match(cmd)
            if m:
                return build_lua_gsub(expr, lua_pattern_escape(m.group(1)), "")

            # -- tr A B --
            m = _RE_TR_REPLACE.match(cmd)
            if m:
                return build_lua_gsub(expr, lua_pattern_escape(m.group(1)), m.group(2))

            # -- awk -F field extraction --
            m = _RE_AWK_F.match(cmd)
            if m:
                delim = m.group(1)
                print_args = m.group(2)
                parts = _RE_AWK_FIELDS.findall(print_args)
                if parts:
                    if not all(is_safe_for_expand(sep) for _, sep in parts if sep):
                        return None
                    lua_parts = []
                    for field_num, separator in parts:
                        if field_num:
                            lua_parts.append(f"t[{field_num}]")
                        elif separator is not None:
                            lua_parts.append(f'"{lua_string_escape(separator)}"')
                    if lua_parts:
                        lua_expr = " .. ".join(lua_parts)
                        esc = lua_string_escape(lua_pattern_escape(delim))
                        return (
                            f'%{{lua:local v=rpm.expand("{lua_string_escape(expr)}") '
                            f"local t={{}} "
                            f'for f in v:gmatch("[^{esc}]+") do t[#t+1]=f end '
                            f"print({lua_expr})}}"
                        )

            # -- sed substitution (handles chained sed commands) --
            substs = parse_sed_substs(cmd)
            if substs:
                if all(is_safe_for_expand(repl) for _, repl, _ in substs):
                    if len(substs) == 1:
                        pattern, repl, is_global = substs[0]
                        return build_lua_gsub(
                            expr,
                            sed_pattern_to_lua(pattern),
                            repl,
                            None if is_global else 1,
                        )
                    esc_expr = lua_string_escape(expr)
                    gsub_calls = []
                    for pattern, repl, is_global in substs:
                        esc_pat = lua_string_escape(sed_pattern_to_lua(pattern))
                        esc_repl = lua_string_escape(lua_gsub_repl_escape(repl))
                        count_arg = "" if is_global else ", 1"
                        gsub_calls.append(
                            f':gsub("{esc_pat}", "{esc_repl}"{count_arg})'
                        )
                    lua_code = f'local v=(rpm.expand("{esc_expr}"){gsub_calls[0]})'
                    for gsub in gsub_calls[1:-1]:
                        lua_code += f" v=(v{gsub})"
                    lua_code += f" print((v{gsub_calls[-1]}))"
                    return f"%{{lua:{lua_code}}}"

            return None

        def convert_glob_removal(expr, op, pat):
            """Convert bash ${var<op><pat>} (suffix/prefix removal) to Lua."""
            is_suffix = "%" in op
            is_longest = len(op) >= 2
            esc_expr = lua_string_escape(expr)

            if pat == "*":
                if is_longest:
                    return '%{lua:print("")}'
                return f'%{{lua:print(rpm.expand("{esc_expr}"))}}'

            # suffix removal: pattern is STR* (literal then star)
            m_cs = re.match(r"^(.+?)(\*|\\?\*)$", pat)
            # prefix removal: pattern is *STR (star then literal)
            m_sc = re.match(r"^(\*|\\?\*)(.+)$", pat)

            if is_suffix and m_cs:
                esc = lua_string_escape(lua_pattern_escape(m_cs.group(1)))
                if is_longest:
                    lua_pat = f"^(.-){esc}"
                else:
                    lua_pat = f"^(.*){esc}"
                return (
                    f'%{{lua:local v=rpm.expand("{lua_string_escape(expr)}") '
                    f'print(v:match("{lua_pat}") or v)}}'
                )

            if not is_suffix and m_sc:
                esc = lua_string_escape(lua_pattern_escape(m_sc.group(2)))
                if is_longest:
                    lua_pat = f".*{esc}(.*)"
                else:
                    lua_pat = f"{esc}(.*)"
                return (
                    f'%{{lua:local v=rpm.expand("{lua_string_escape(expr)}") '
                    f'print(v:match("{lua_pat}") or v)}}'
                )

            return None

        # --- var=macro; echo ${var:off[:len]} → %{sub} ---
        m = _RE_SUBSTR.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                offset = int(m.group(3))
                length_raw = m.group(4)
                start = offset + 1
                if length_raw is not None:
                    if length_raw.isdigit():
                        return f"%{{sub {expr}, {start}, {offset + int(length_raw)}}}"
                    length_macro = normalize_macro(length_raw)
                    if length_macro is not None:
                        if offset == 0:
                            return f"%{{sub {expr}, {start}, {length_macro}}}"
                        return f"%{{sub {expr}, {start}, %[{length_macro} + {offset}]}}"
                else:
                    return f"%{{sub {expr}, {start}}}"

        # --- var=macro; echo ${var//PAT/REPL} → Lua gsub ---
        m = _RE_BASH_REPLACE.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                is_global = m.group(3) == "//"
                pat = m.group(4)
                repl = strip_quotes(m.group(5))
                if is_safe_for_expand(repl):
                    lua_pat = lua_pattern_escape(pat)
                    return build_lua_gsub(expr, lua_pat, repl, None if is_global else 1)

        # --- var=macro; echo ${var,,} → %{lower:} ---
        m = _RE_BASH_LOWER.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                return f"%{{lower:{expr}}}"

        # --- var=macro; echo ${var^^} → %{upper:} ---
        m = _RE_BASH_UPPER.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                return f"%{{upper:{expr}}}"

        # --- echo EXPR | CMD (pipe pattern) ---
        m = _RE_PIPE.match(body)
        if m:
            expr = normalize_macro(m.group(1))
            if expr is not None:
                cmd = m.group(2).strip()
                result = convert_string_op(expr, cmd)
                if result:
                    return result

        # --- CMD <<< EXPR (herestring pattern) ---
        m = _RE_HERESTRING.match(body)
        if m:
            cmd = m.group(1).strip()
            expr = normalize_macro(m.group(2))
            if expr is not None:
                result = convert_string_op(expr, cmd)
                if result:
                    return result

        # --- var=macro; echo $var | CMD → delegate to convert_string_op ---
        m = _RE_VAR_PIPE.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                cmd = m.group(3).strip()
                result = convert_string_op(expr, cmd)
                if result:
                    return result

        # --- var=macro; CMD <<< $var → delegate to convert_string_op ---
        m = _RE_VAR_HERESTRING.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                cmd = m.group(3).strip()
                result = convert_string_op(expr, cmd)
                if result:
                    return result

        # --- var=macro; echo ${var%%PAT} / ${var%PAT} → suffix removal ---
        m = _RE_BASH_SUFFIX.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                op = m.group(3)
                pat = m.group(4)
                result = convert_glob_removal(expr, op, pat)
                if result:
                    return result

        # --- var=macro; echo ${var##PAT} / ${var#PAT} → prefix removal ---
        m = _RE_BASH_PREFIX.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                op = m.group(3)
                pat = m.group(4)
                result = convert_glob_removal(expr, op, pat)
                if result:
                    return result

        # --- date +FORMAT → %{lua:print(os.date(FMT))} ---
        m = _RE_DATE_SIMPLE.match(body)
        if m:
            fmt = m.group(1)
            if is_safe_for_expand(fmt):
                utc_prefix = "!" if _RE_DATE_UTC.match(body) else ""
                return (
                    f'%{{lua:print(os.date("{lua_string_escape(utc_prefix + fmt)}"))}}'
                )

        # --- echo $((EXPR)) → %[EXPR] ---
        m = _RE_ARITHMETIC.match(body)
        if m:
            inner = m.group(1).strip()
            if is_safe_for_expand(inner):
                return f"%[{inner}]"

        # --- basename %{macro} → Lua ---
        m = _RE_BASENAME.match(body)
        if m:
            expr = normalize_macro(m.group(1))
            if expr is not None:
                return f'%{{lua:print((rpm.expand("{lua_string_escape(expr)}"):match("[^/]+$")))}}'

        # --- dirname %{macro} → Lua ---
        m = _RE_DIRNAME.match(body)
        if m:
            expr = normalize_macro(m.group(1))
            if expr is not None:
                return f'%{{lua:print((rpm.expand("{lua_string_escape(expr)}"):match("^(.*)/")))}}'

        # --- test "A" OP "B" && echo X || echo Y → Lua ---
        m = _RE_TEST_STR.match(body)
        if m:
            a, op, b, x, y = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            if all(is_safe_for_expand(v) for v in (a, b, x, y)):
                lua_op = "~=" if op == "!=" else "=="
                return (
                    f'%{{lua:print(rpm.expand("{lua_string_escape(a)}") {lua_op}'
                    f' rpm.expand("{lua_string_escape(b)}")'
                    f' and "{lua_string_escape(x)}" or "{lua_string_escape(y)}")}}'
                )

        # --- [ -z "EXPR" ] && echo A || echo B → Lua ---
        m = _RE_TEST_EMPTY.match(body)
        if m:
            expr_val, a, b = m.group(1), m.group(2), m.group(3)
            if all(is_safe_for_expand(v) for v in (expr_val, a, b)):
                return (
                    f'%{{lua:print(rpm.expand("{lua_string_escape(expr_val)}") == ""'
                    f' and "{lua_string_escape(a)}" or "{lua_string_escape(b)}")}}'
                )

        # --- printf %.Ns MACRO → %{sub MACRO, 1, N} ---
        m = _RE_PRINTF_TRUNC.match(body)
        if m:
            n = int(m.group(1))
            expr = normalize_macro(m.group(2))
            if expr is not None:
                return f"%{{sub {expr}, 1, {n}}}"

        # --- printf %.Nf MACRO → Lua string.format ---
        m = _RE_PRINTF_FLOAT.match(body)
        if m:
            n = int(m.group(1))
            expr = normalize_macro(m.group(2))
            if expr is not None:
                return (
                    f'%{{lua:print(string.format("%%.{n}f", '
                    f'tonumber(rpm.expand("{lua_string_escape(expr)}"))))}}'
                )

        # --- var=MACRO; arr=(${var//DELIM/ }); echo ${arr[N]} → field extraction ---
        m = _RE_BASH_ARRAY_FIELD.match(body)
        if m:
            expr = normalize_macro(m.group(2))
            if expr is not None:
                delim = m.group(4)
                field = int(m.group(5)) + 1
                return build_lua_field(expr, delim, field)

        # --- echo %{macro} EXTRA (simple concatenation, no pipe) ---
        m = _RE_ECHO_CONCAT.match(body)
        if m and "|" not in m.group(2):
            expr = normalize_macro(m.group(1))
            extra = m.group(2).strip()
            if expr is not None and is_safe_for_expand(extra):
                return f"{expr} {extra}"

        return "%{nil}"

    @staticmethod
    def is_lua_safe(code):
        def has_safe_format_specs(fmt):
            """
            Check that a format string only uses safe specifiers.

            Accounts for RPM ``%%`` → ``%`` expansion before checking
            Lua ``string.format`` specifiers.  Allows numeric types
            and ``%%``; blocks ``%c``, ``%s``, ``%q`` and anything
            else that could produce a ``%`` character.
            """
            expanded = fmt.replace("%%", "%")
            cleaned = _SAFE_FORMAT_SPEC_RE.sub("", expanded)
            return "%" not in cleaned

        stripped = _strip_lua_comments(code)
        string_spans = []
        for m in _LUA_STRING_LITERAL_RE.finditer(stripped):
            content = m.group(0)[1:-1]
            if _UNSAFE_LUA_STRING_CONTENT_RE.search(content):
                return False
            decoded = _decode_lua_escapes(content)
            if _UNSAFE_LUA_STRING_CONTENT_RE.search(decoded):
                return False
            if decoded.endswith("%"):
                return False
            string_spans.append((m.start(), m.end()))
        for m in _FORMAT_CALL_RE.finditer(stripped):
            if any(s <= m.start() < e for s, e in string_spans):
                continue
            fmt_match = _FORMAT_LITERAL_ARG_RE.match(stripped, m.end())
            if not fmt_match or not has_safe_format_specs(fmt_match.group(1)):
                return False
        stripped = _LUA_STRING_LITERAL_RE.sub('""', stripped)
        if _UNSAFE_LUA_BRACKET_RE.search(stripped):
            return False
        if _LUA_COLON_UNSAFE_METHOD_RE.search(stripped):
            return False
        for m in _RPM_EXPAND_REF_RE.finditer(stripped):
            if not _RPM_EXPAND_SAFE_CALL_RE.match(stripped, m.end()):
                return False
        safe_spans = []
        for m in _LUA_DOTTED_RE.finditer(stripped):
            mod, member = m.group(1), m.group(2)
            if mod in _SAFE_LUA_DOTTED_MODULES:
                if mod == "string" and member in (
                    "dump",
                    "char",
                    "sub",
                    "find",
                    "reverse",
                    "rep",
                ):
                    return False
                if mod == "string" and member == "format":
                    rest = stripped[m.end() :].lstrip()
                    if not rest.startswith("("):
                        return False
                safe_spans.append((m.start(), m.end()))
                continue
            if f"{mod}.{member}" in _SAFE_LUA_DOTTED:
                safe_spans.append((m.start(), m.end()))
                continue
            return False
        for m in _LUA_IDENT_RE.finditer(stripped):
            if m.group(1) in _UNSAFE_LUA_IDENTIFIERS:
                if not any(s <= m.start() and m.end() <= e for s, e in safe_spans):
                    return False
        return True

    _MAX_SANITIZE_DEPTH = 64

    @classmethod
    def sanitize(cls, value: str, _depth: int = 0) -> Tuple[str, int, int]:
        """
        Sanitizes a spec file content or an expression by removing shell expansions
        and impure Lua macros, replacing them with safe equivalents or `%{nil}`.

        Also removes `%include`, `%load` and `%uncompress` directives since
        they reference external files or run external commands.

        Args:
            value: String to be sanitized, can be a spec file content
                or an arbitrary macro expression.

        Returns:
            Tuple of (sanitized string, number of converted shell expansions,
            number of removed unsafe constructs).
        """
        if _depth >= cls._MAX_SANITIZE_DEPTH:
            return "%{nil}", 0, 1

        converted = 0
        removed = 0

        def is_name_safe(name):
            try:
                sanitized, _, _ = cls.sanitize(name, _depth + 1)
            except UnterminatedMacroException:
                return False
            return sanitized == name

        def sanitize_nodes(nodes):
            nonlocal converted, removed
            result = []
            i = 0
            while i < len(nodes):
                node = nodes[i]
                if isinstance(
                    node,
                    (
                        MacroSubstitution,
                        EnclosedMacroSubstitution,
                        SingleArgEnclosedMacroSubstitution,
                    ),
                ) and node.name in ("include", "load", "uncompress"):
                    removed += 1
                    # %include/%load followed by whitespace and argument
                    if isinstance(node, MacroSubstitution):
                        i += 1
                        while i < len(nodes):
                            s = str(nodes[i])
                            i += 1
                            m = _UNESCAPED_NEWLINE_RE.search(s)
                            if m:
                                result.append(s[m.start() :])
                                break
                    else:
                        i += 1
                    continue
                if isinstance(node, ConditionalMacroExpansion):
                    if not is_name_safe(node.name):
                        removed += 1
                        result.append("%{nil}")
                    else:
                        body = sanitize_nodes(node.body)
                        result.append(f"%{{{node.prefix}{node.name}:{body}}}")
                elif isinstance(node, ExpressionExpansion):
                    sanitized_body, c, r = cls.sanitize(node.body, _depth + 1)
                    converted += c
                    removed += r
                    m = _EXPRESSION_LUA_PREFIX_RE.match(sanitized_body)
                    if m:
                        lua_code = sanitized_body[m.end() :]
                        if not cls.is_lua_safe(lua_code):
                            removed += 1
                            result.append("%{nil}")
                        else:
                            result.append(f"%[{sanitized_body}]")
                    else:
                        result.append(f"%[{sanitized_body}]")
                elif type(node) is ShellExpansion:
                    replacement = cls.sanitize_shell_expansion(node.body)
                    if replacement == "%{nil}":
                        removed += 1
                    elif (
                        replacement.startswith("%{lua:")
                        and replacement.endswith("}")
                        and not cls.is_lua_safe(replacement[6:-1])
                    ):
                        replacement = "%{nil}"
                        removed += 1
                    else:
                        converted += 1
                    result.append(replacement)
                elif isinstance(node, SingleArgEnclosedMacroSubstitution):
                    if not is_name_safe(node.name):
                        removed += 1
                        result.append("%{nil}")
                    elif node.name == "lua":
                        if not cls.is_lua_safe(node.arg):
                            removed += 1
                            result.append("%{nil}")
                        else:
                            result.append(str(node))
                    else:
                        sanitized_body, c, r = cls.sanitize(node.arg, _depth + 1)
                        converted += c
                        removed += r
                        result.append(f"%{{{node.name}:{sanitized_body}}}")
                elif isinstance(node, EnclosedMacroSubstitution):
                    if not is_name_safe(node.name):
                        removed += 1
                        result.append("%{nil}")
                    elif node.args:
                        sanitized_args = []
                        for arg in node.args:
                            try:
                                sanitized_arg, c, r = cls.sanitize(arg, _depth + 1)
                            except UnterminatedMacroException:
                                sanitized_arg = "%{nil}"
                                c, r = 0, 1
                            converted += c
                            removed += r
                            sanitized_args.append(sanitized_arg)
                        args_str = " " + " ".join(sanitized_args)
                        result.append(f"%{{{node.prefix}{node.name}{args_str}}}")
                    else:
                        result.append(str(node))
                else:
                    result.append(str(node))
                i += 1
            return "".join(result)

        sanitized = sanitize_nodes(ValueParser.parse(value))
        return sanitized, converted, removed
