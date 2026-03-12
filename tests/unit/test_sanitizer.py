# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import pytest

from specfile.sanitizer import Sanitizer


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "c=%{commit}; echo ${c:0:7}",
            "%{sub %{commit} 1 7}",
        ),
        (
            "c=%{commit};echo ${c:0:7}",
            "%{sub %{commit} 1 7}",
        ),
        (
            "c=%{commit0}; echo ${c:0:7}",
            "%{sub %{commit0} 1 7}",
        ),
        (
            "foo=%{version}; echo ${foo:0:5}",
            "%{sub %{version} 1 5}",
        ),
        (
            "foo=%{version}; echo ${foo:6}",
            "%{sub %{version} 7}",
        ),
        (
            "l=%{_lib}; echo ${l:3}",
            "%{sub %{_lib} 4}",
        ),
        (
            "c=%{version}; echo ${c:12:4}",
            "%{sub %{version} 13 16}",
        ),
        (
            "c=%{commit}; echo ${c:0:%{commit_abbrev}}",
            "%{sub %{commit} 1 %{commit_abbrev}}",
        ),
        (
            'c="%{git_commit}"; echo "${c:0:8}"',
            "%{sub %{git_commit} 1 8}",
        ),
        (
            "n=%{modname}; echo ${n:0:1}",
            "%{sub %{modname} 1 1}",
        ),
    ],
)
def test_substring_extraction(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "v=%{version}; echo ${v//./_}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
        (
            "v=%{version}; echo ${v//./}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "")))}',
        ),
        (
            "n=%{name}; echo ${n//-/_}",
            '%{lua:print((rpm.expand("%{name}"):gsub("%-", "_")))}',
        ),
        (
            'b=%{built_tag_strip}; echo ${b/-/"~"}',
            '%{lua:print((rpm.expand("%{built_tag_strip}"):gsub("%-", "~", 1)))}',
        ),
        (
            "n=%{srcname}; echo ${n//-/.}",
            '%{lua:print((rpm.expand("%{srcname}"):gsub("%-", ".")))}',
        ),
        (
            "v=%{version}; echo ${v//./-}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "-")))}',
        ),
        (
            "d=%{inkscape_date}; echo ${d//-/}",
            '%{lua:print((rpm.expand("%{inkscape_date}"):gsub("%-", "")))}',
        ),
        (
            'rel="%{releasenum}"; echo "${rel//-/}"',
            '%{lua:print((rpm.expand("%{releasenum}"):gsub("%-", "")))}',
        ),
        # % in replacement must be escaped as %% for Lua gsub
        (
            "v=%{version}; echo ${v//./%2F}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "%%2F")))}',
        ),
    ],
)
def test_bash_replacement(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            't="%{Bg_Name}";echo ${t,,}',
            "%{lower:%{Bg_Name}}",
        ),
        (
            "v=%{name}; echo ${v^^}",
            "%{upper:%{name}}",
        ),
    ],
)
def test_case_conversion(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "ver=%{version}; echo ${ver%%%%.*}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match("^(.-)%.") or v)}',
        ),
        (
            "v=%{version}; echo ${v%.*}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match("^(.*)%.") or v)}',
        ),
        # bare * with longest match → empty string
        (
            "v=%{version}; echo ${v%%%%*}",
            '%{lua:print("")}',
        ),
        # bare * with shortest match → original value
        (
            "v=%{version}; echo ${v%*}",
            '%{lua:print(rpm.expand("%{version}"))}',
        ),
    ],
)
def test_suffix_removal(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "v=%{version}; echo ${v##*.}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match(".*%.(.*)") or v)}',
        ),
        (
            "v=%{version}; echo ${v#*.}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match("%.(.*)") or v)}',
        ),
        # pattern containing #
        (
            "v=%{version}; echo ${v#*#}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match("#(.*)") or v)}',
        ),
        (
            "v=%{version}; echo ${v##*#}",
            '%{lua:local v=rpm.expand("%{version}") print(v:match(".*#(.*)") or v)}',
        ),
        # bare * with longest match → empty string
        (
            "v=%{version}; echo ${v##*}",
            '%{lua:print("")}',
        ),
        # bare * with shortest match → original value
        (
            "v=%{version}; echo ${v#*}",
            '%{lua:print(rpm.expand("%{version}"))}',
        ),
    ],
)
def test_prefix_removal(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo %{version} | cut -d. -f3",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==3 then print(f) break end end}",
        ),
        (
            "echo %{version} | cut -d. -f1-2",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(table.concat(t,".",1,2))}',
        ),
        (
            "echo %{version} | cut -d. -f1",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "echo %{version} | cut -d. -f1-2",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(table.concat(t,".",1,2))}',
        ),
        (
            "echo %{version} | cut -d. -f-2",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(table.concat(t,".",1,2))}',
        ),
        (
            "echo %{version} | cut -d '^' -f 1",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%^]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "echo %{version} | cut -d'-' -f 1",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%-]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "echo %{version} | cut -d. -f1-3",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(table.concat(t,".",1,3))}',
        ),
    ],
)
def test_pipe_to_cut(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo %{git_commit} | cut -c -8",
            "%{sub %{git_commit} 1 8}",
        ),
        (
            "echo %{gitcommit} | cut -c 1-8",
            "%{sub %{gitcommit} 1 8}",
        ),
        (
            "echo %{snapshot_rev} | cut -c1-6",
            "%{sub %{snapshot_rev} 1 6}",
        ),
    ],
)
def test_pipe_to_cut_bytes(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo \"%{name}\" | tr '[:upper:]' '[:lower:]'",
            "%{lower:%{name}}",
        ),
        (
            "echo %{upstream_prever} | tr '[:upper:]' '[:lower:]'",
            "%{lower:%{upstream_prever}}",
        ),
        (
            "echo %{version} | tr . _",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
        (
            "echo '%{version}' | tr '^' '.'",
            '%{lua:print((rpm.expand("%{version}"):gsub("%^", ".")))}',
        ),
        (
            "echo '%{version}' | tr -d .",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "")))}',
        ),
        (
            "echo '%{version}' | tr -d '~'",
            '%{lua:print((rpm.expand("%{version}"):gsub("~", "")))}',
        ),
        (
            "echo %{date} | tr -d -",
            '%{lua:print((rpm.expand("%{date}"):gsub("%-", "")))}',
        ),
    ],
)
def test_pipe_to_tr(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo %{version} | sed 's/\\./-/g'",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "-")))}',
        ),
        (
            "echo %{version} | sed 's|\\.|_|g'",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
        (
            "echo %{py3_shebang_flags} | sed 's|s||'",
            '%{lua:print((rpm.expand("%{py3_shebang_flags}"):gsub("s", "", 1)))}',
        ),
        (
            'echo %{version} | sed "s/\\./_/g"',
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
        (
            "echo %{unversion} | sed 's/_/./g'",
            '%{lua:print((rpm.expand("%{unversion}"):gsub("_", ".")))}',
        ),
        (
            "echo 1.2.3-rc4 | sed 's/-/~/g'",
            '%{lua:print((rpm.expand("%{quote:1.2.3-rc4}"):gsub("-", "~")))}',
        ),
        (
            "echo %{version} | sed 's/\\\\./_/g'",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
    ],
)
def test_pipe_to_sed(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


def test_chained_sed():
    assert Sanitizer.sanitize_shell_expansion(
        "echo %{tag} | sed -e 's|.00$||' | sed -e 's|\\.||g'"
    ) == (
        '%{lua:local v=(rpm.expand("%{tag}"):gsub(".00$", "", 1))'
        ' print((v:gsub("%.", "")))}'
    )


def test_chained_sed_rpm_escaped():
    assert Sanitizer.sanitize_shell_expansion(
        "echo '%canonical_project_name' | sed --regexp-extended 's:-:_:g;s:\\\\.:_:g'"
    ) == (
        '%{lua:local v=(rpm.expand("%{canonical_project_name}"):gsub("-", "_"))'
        ' print((v:gsub("%.", "_")))}'
    )


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo %{version} | awk -F. '{print $1\".\"$2}'",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(t[1] .. "." .. t[2])}',
        ),
        (
            "echo %{version} | awk -F. '{print $1}'",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            " print(t[1])}",
        ),
    ],
)
def test_pipe_to_awk(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "tr . _ <<< %{version}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
        (
            "tr - . <<< %{upstreamver}",
            '%{lua:print((rpm.expand("%{upstreamver}"):gsub("%-", ".")))}',
        ),
        (
            "cut -d. -f1 <<< %{version}",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "cut -d. -f1-2 <<< %{version}",
            '%{lua:local v=rpm.expand("%{version}") local t={}'
            ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
            ' print(table.concat(t,".",1,2))}',
        ),
        (
            "cut -b -7 <<< %{emacscommit}",
            "%{sub %{emacscommit} 1 7}",
        ),
        (
            "tr -d . <<< %{version}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "")))}',
        ),
        (
            "sed 's/\\.//g' <<<%{version}",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "")))}',
        ),
        (
            "sed 's/-/~/g' <<<1.2.3-rc4",
            '%{lua:print((rpm.expand("%{quote:1.2.3-rc4}"):gsub("-", "~")))}',
        ),
    ],
)
def test_herestring(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "c=%{version}; echo $c | cut -d. -f1",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "v=%{version}; tr . _ <<< $v",
            '%{lua:print((rpm.expand("%{version}"):gsub("%.", "_")))}',
        ),
    ],
)
def test_variable_indirection(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "foo=%{version}; a=(${foo//./ }); echo ${a[0]} ",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==1 then print(f) break end end}",
        ),
        (
            "foo=%{version}; a=(${foo//./ }); echo ${a[1]} ",
            '%{lua:local v=rpm.expand("%{version}") local i=0'
            ' for f in v:gmatch("[^%.]+") do i=i+1'
            " if i==2 then print(f) break end end}",
        ),
    ],
)
def test_bash_array_field(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            'date +"%Y%m%d"',
            '%{lua:print(os.date("%Y%m%d"))}',
        ),
        (
            "date +'%Y%m%d'",
            '%{lua:print(os.date("%Y%m%d"))}',
        ),
        (
            "date -u +'%Y-%m-%dT%H:%M:%SZ'",
            '%{lua:print(os.date("!%Y-%m-%dT%H:%M:%SZ"))}',
        ),
        (
            'date +"%Y-%d-%m"',
            '%{lua:print(os.date("%Y-%d-%m"))}',
        ),
    ],
)
def test_date_formatting(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        ("echo $((%{__isa_bits}+0))", "%[%{__isa_bits}+0]"),
        ("echo $((%{__isa_bits}+2))", "%[%{__isa_bits}+2]"),
        ("echo $((%{ver_minor}+1))", "%[%{ver_minor}+1]"),
        ("echo $((%{sover}-1))", "%[%{sover}-1]"),
        (" echo $(( %majorversion + 1 )) ", "%[%majorversion + 1]"),
    ],
)
def test_arithmetic(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "basename %{_python3_include}",
            '%{lua:print((rpm.expand("%{_python3_include}"):match("[^/]+$")))}',
        ),
        (
            "dirname %{bashcompdir}",
            '%{lua:print((rpm.expand("%{bashcompdir}"):match("^(.*)/")))}',
        ),
        (
            "dirname %{compdir}",
            '%{lua:print((rpm.expand("%{compdir}"):match("^(.*)/")))}',
        ),
    ],
)
def test_basename_dirname(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


def test_string_comparison_not_equal():
    assert Sanitizer.sanitize_shell_expansion(
        'test "%{_libdir}" != "/usr/lib" && echo 1 || echo 0'
    ) == (
        '%{lua:print(rpm.expand("%{_libdir}") ~= rpm.expand("/usr/lib")'
        ' and "1" or "0")}'
    )


def test_string_comparison_equal():
    assert Sanitizer.sanitize_shell_expansion(
        'test "%{OTHER}" == "1" && echo fedora || echo redhat'
    ) == (
        '%{lua:print(rpm.expand("%{OTHER}") == rpm.expand("1")'
        ' and "fedora" or "redhat")}'
    )


def test_empty_test():
    assert Sanitizer.sanitize_shell_expansion(
        '[ -z "%{?flag}" ] && echo A || echo B'
    ) == ('%{lua:print(rpm.expand("%{?flag}") == ""' ' and "A" or "B")}')


def test_printf_truncation():
    assert (
        Sanitizer.sanitize_shell_expansion("printf %%.7s %commit")
        == "%{sub %{commit} 1 7}"
    )


def test_printf_float():
    assert Sanitizer.sanitize_shell_expansion(
        'LANG=C printf "%.4f" %{cpan_version}'
    ) == (
        '%{lua:print(string.format("%%.4f",'
        ' tonumber(rpm.expand("%{cpan_version}"))))}'
    )


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "echo %{optflags} -fno-strict-aliasing",
            "%{optflags} -fno-strict-aliasing",
        ),
        (
            "echo %{build_ldflags} -fuse-ld=lld",
            "%{build_ldflags} -fuse-ld=lld",
        ),
        (
            "echo %{optflags} -D_DEFAULT_SOURCE",
            "%{optflags} -D_DEFAULT_SOURCE",
        ),
        (
            "echo %{optflags} -Wno-error=dangling-reference",
            "%{optflags} -Wno-error=dangling-reference",
        ),
    ],
)
def test_echo_concat(body, expected):
    assert Sanitizer.sanitize_shell_expansion(body) == expected


def test_cut_bytes_with_macro_offset():
    assert (
        Sanitizer.sanitize_shell_expansion("cut -b %{rmprefix}- <<<'%{_bindir}'")
        == "%{sub %{_bindir} %{rmprefix}}"
    )


@pytest.mark.parametrize(
    "body",
    [
        "octave-config -p VERSION || echo 0",
        "python3-config --abiflags",
        "pkg-config --modversion qwt",
        "/usr/bin/getconf _NPROCESSORS_ONLN",
        "uname -m",
        "hostname",
        "id -un",
        "mktemp --directory",
        "ruby -rrbconfig -e \"puts RbConfig::CONFIG['vendorlibdir']\"",
    ],
)
def test_unconvertible_returns_nil(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "code",
    [
        'print(rpm.expand("%{version}"))',
        'print((rpm.expand("%{version}"):gsub("%.", "_")))',
        'print(os.date("%Y%m%d"))',
        'print(os.date("!%Y-%m-%dT%H:%M:%SZ"))',
        "print(os.clock())",
        "print(os.time())",
        "print(os.difftime(os.time(), 0))",
        'local v=rpm.expand("%{version}") print(v:match("^(.-)%.") or v)',
        'local v=rpm.expand("%{version}") local t={}'
        ' for f in v:gmatch("[^%.]+") do t[#t+1]=f end'
        ' print(table.concat(t,".",1,2))',
        'print(string.len("hello"))',
        "print(math.floor(3.7))",
        "print(math.max(1, 2, 3))",
        'print(table.concat({"a", "b"}, ","))',
        "print(tostring(42))",
        'print(tonumber("42"))',
        'print(type("hello"))',
        "local x = 1 print(x)",
        'print(string.format("%.4f", tonumber(rpm.expand("%{version}"))))',
        'print(string.format("%d", 42))',
        'print(string.format("%%.4f", tonumber(rpm.expand("%{version}"))))',
        # Comments inside safe code
        'print(rpm.expand("%{version}")) -- a comment',
        "local x = 1 --[[ block comment ]] print(x)",
    ],
)
def test_lua_safe_code(code):
    assert Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'os.execute("id")',
        'os.remove("/tmp/foo")',
        'os.rename("/tmp/a", "/tmp/b")',
        "os.exit(0)",
        'io.open("/etc/passwd")',
        'io.popen("id")',
        'io.lines("/etc/passwd")',
        "io.tmpfile()",
        'require("os")',
        'dofile("/tmp/evil.lua")',
        'loadfile("/tmp/evil.lua")',
        "loadstring(\"os.execute('id')\")()",
        "load(\"os.execute('id')\")()",
        "debug.getinfo(1)",
        "debug.getregistry()",
        'package.loadlib("/lib/libc.so.6", "system")',
        "collectgarbage()",
        "coroutine.create(function() end)",
        'rpm.define("evil_macro 1")',
        'rpm.undefine("Name")',
        "rpm.register(function() end)",
        'rpm.execute("id")',
        'rpm.redirect2macro("foo")',
        'posix.exec("/bin/sh")',
        'fedora.rpm.vercmp("1", "2")',
        "string.dump(print)",
        "string.char(37, 40)",
        'string.sub("hello", 1, 3)',
        'string.find("hello", "l")',
        'string.reverse("hello")',
        'string.rep("x", 5)',
        'string.format("%c", 37)',
        'string.format("%s", "hello")',
        'string.format("%q", "hello")',
        "string.format(var)",
    ],
)
def test_lua_unsafe_direct_calls(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        '_G["os"]["execute"]("id")',
        "_G['os']['execute']('id')",
        'rawget(_G, "os")',
        'rawset(_G, "evil", function() end)',
        "rawequal(_G, _G)",
        "getfenv(0)",
        "setfenv(1, {})",
        'getmetatable("")',
        "setmetatable({}, {})",
        "newproxy(true)",
        'module("evil")',
        "pcall(load, \"os.execute('id')\")",
        "xpcall(load, print, \"os.execute('id')\")",
        "pcall(function() end)",
        "xpcall(function() end, print)",
    ],
)
def test_lua_unsafe_identifiers(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'local x = {}; x["os"] = true',
        "local x = {}; x['cmd'] = 'id'",
        'os["\\".."]',
        "os[string.char(101,120,101,99,117,116,101)]()",
        "os[[[execute]]]()",
        "os[var]",
    ],
)
def test_lua_unsafe_bracket_notation(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'local e = _G e.os.execute("id")',
        "local r = rawget print(r)",
        "local d = debug d.getinfo(1)",
        'local i = io i.popen("id")',
        'local l = loadstring l("print(1)")()',
        'local p = package p.loadlib("x", "y")',
    ],
)
def test_lua_unsafe_variable_aliasing(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'os . execute("id")',
        'os  .  execute("id")',
        'os\t.\texecute("id")',
    ],
)
def test_lua_unsafe_spaced_dot(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        '(os).execute("id")',
        '((os)).execute("id")',
        '(rpm).define("evil 1")',
        "(string).dump(print)",
    ],
)
def test_lua_unsafe_paren_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'os:execute("id")',
        "os:exit(0)",
        'rpm:define("evil 1")',
    ],
)
def test_lua_unsafe_colon_access(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'os.--[[comment]]execute("id")',
        "os.--[[x]]exit(0)",
    ],
)
def test_lua_unsafe_comment_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        '--[=[ ]=] os.execute("id")',
        '--[==[ ]==] os.execute("id")',
        'print("safe" --[=[ ]=]) os.execute("id")',
        '--[===[ ]===] io.popen("id")',
    ],
)
def test_lua_unsafe_long_comment_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'rpm.expand("%(whoami)")',
        "rpm.expand(\"%{lua:os.execute('id')}\")",
        'print(rpm.expand("%(cat /etc/passwd)"))',
        "rpm.expand('%(id)')",
        'local x = rpm.expand("%(uname -a)") print(x)',
        'rpm.expand("%{load:/tmp/evil.lua}")',
        'rpm.expand("%{include:/tmp/evil.spec}")',
        'rpm.expand("%{uncompress:/tmp/file.gz}")',
        'print(rpm.expand("%{load: /tmp/evil.lua}"))',
        'rpm.expand("%{uncompress: file}")',
        'rpm.expand("%{expand:%(whoami)}")',
        "rpm.expand(\"%{expand:%{lua:os.execute('id')}}\")",
        'rpm.expand("%{define:evil %(whoami)}")',
        'rpm.expand("%{global:evil %(whoami)}")',
        'rpm.expand("%{define:Name evil}")',
        'rpm.expand("%{global:_prefix /tmp/evil}")',
        'rpm.expand("%{undefine:Name}")',
        'rpm.expand("%{define :__spec_check_post exit 0}")',
        'rpm.expand("%load /tmp/evil.lua")',
        'rpm.expand("%include /tmp/evil.spec")',
        'rpm.expand("%define __spec_check_post exit 0")',
        'rpm.expand("%global _prefix /tmp/evil")',
        'rpm.expand("%undefine Name")',
    ],
)
def test_lua_unsafe_rpm_expand_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        "local e = _ENV",
        '_ENV.os.execute("id")',
    ],
)
def test_lua_unsafe_env(code):
    assert not Sanitizer.is_lua_safe(code)


def test_lua_rpm_expand_shell_bypass_in_sanitize():
    value = '%{lua:print(rpm.expand("%(whoami)"))}'
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


def test_lua_rpm_expand_nested_lua_bypass_in_sanitize():
    value = """%{lua:rpm.expand("%{lua:os.execute('id')}")}"""
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


@pytest.mark.parametrize(
    "code",
    [
        'rpm.expand(string.char(37, 40) .. "whoami)")',
        'rpm.expand(string.format("%%") .. "(whoami)")',
        'rpm.expand(string.reverse(")imaohw(%"))',
        'rpm.expand(("%%"):format() .. "(whoami)")',
        'rpm.expand("" .. "")',
        "local f = rpm.expand",
        "x = rpm.expand",
        "rpm.expand(x)",
    ],
)
def test_lua_unsafe_rpm_expand_dynamic_args(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "value",
    [
        '%{lua:rpm.expand(string.char(37, 40) .. "whoami)")}',
        '%{lua:rpm.expand(string.format("%%") .. "(whoami)")}',
        '%{lua:rpm.expand(string.reverse(")imaohw(%"))}',
        '%{lua:rpm.expand(("%%"):format() .. "(whoami)")}',
    ],
)
def test_lua_rpm_expand_string_construction_bypass_in_sanitize(value):
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


def test_lua_unsafe_in_sanitize():
    value = '%{lua:os.execute("id")}'
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


def test_lua_safe_in_sanitize():
    value = '%{lua:print(rpm.expand("%{version}"))}'
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == value
    assert removed == 0


def test_lua_bracket_bypass_in_sanitize():
    value = '%{lua:_G["os"]["execute"]("id")}'
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


@pytest.mark.parametrize(
    "value",
    [
        '%{lua:print(rpm.expand("%{load:/tmp/evil.lua}"))}',
        '%{lua:print(rpm.expand("%{include:/tmp/evil.spec}"))}',
        '%{lua:print(rpm.expand("%{uncompress:/tmp/file.gz}"))}',
    ],
)
def test_lua_load_include_uncompress_bypass_in_sanitize(value):
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


@pytest.mark.parametrize(
    "value",
    [
        '%{lua:print(rpm.expand("%{expand:%(whoami)}"))}',
        "%{lua:print(rpm.expand(\"%{expand:%{lua:os.execute('id')}}\"))}",
        '%{lua:print(rpm.expand("%{define:evil %(whoami)}"))}',
        '%{lua:print(rpm.expand("%{global:evil %(whoami)}"))}',
    ],
)
def test_lua_rpm_expand_define_global_bypass_in_sanitize(value):
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


@pytest.mark.parametrize(
    "value",
    [
        '%{lua:rpm.expand("%load /tmp/evil.lua")}',
        '%{lua:rpm.expand("%include /tmp/evil.spec")}',
        '%{lua:rpm.expand("%define __spec_check_post exit 0")}',
        '%{lua:rpm.expand("%global _prefix /tmp/evil")}',
        '%{lua:rpm.expand("%undefine Name")}',
    ],
)
def test_lua_rpm_expand_braceless_directive_bypass_in_sanitize(value):
    sanitized, converted, removed = Sanitizer.sanitize(value)
    assert sanitized == "%{nil}"
    assert removed == 1


@pytest.mark.parametrize(
    "value, expected_sanitized, expected_removed",
    [
        (
            "%{expand:%(whoami)}",
            "%{expand:%{nil}}",
            1,
        ),
        (
            "%{lower:%(whoami)}",
            "%{lower:%{nil}}",
            1,
        ),
        (
            "%{upper:%(whoami)}",
            "%{upper:%{nil}}",
            1,
        ),
        (
            '%{expand:%{lua:os.execute("id")}}',
            "%{expand:%{nil}}",
            1,
        ),
        (
            "%{lower:%{name}}",
            "%{lower:%{name}}",
            0,
        ),
        (
            "%{quote:%(cat /etc/passwd)}",
            "%{quote:%{nil}}",
            1,
        ),
        (
            "%{uncompress:/tmp/file.gz}",
            "",
            1,
        ),
    ],
)
def test_builtin_macro_body_sanitized(value, expected_sanitized, expected_removed):
    sanitized, _, removed = Sanitizer.sanitize(value)
    assert sanitized == expected_sanitized
    assert removed == expected_removed


@pytest.mark.parametrize(
    "value, expected_sanitized, expected_removed",
    [
        (
            "%{upper %(whoami)}",
            "%{upper %{nil}}",
            1,
        ),
        (
            "%{macro %(whoami) %{version}}",
            "%{macro %{nil} %{version}}",
            1,
        ),
        (
            "%{macro %(whoami) %(id)}",
            "%{macro %{nil} %{nil}}",
            2,
        ),
        (
            "%{foo %{version}}",
            "%{foo %{version}}",
            0,
        ),
    ],
)
def test_enclosed_macro_args_sanitized(value, expected_sanitized, expected_removed):
    sanitized, _, removed = Sanitizer.sanitize(value)
    assert sanitized == expected_sanitized
    assert removed == expected_removed


@pytest.mark.parametrize(
    "body",
    [
        "v=%{version}; echo ${v//./%(whoami)}",
        "v=%{version}; echo ${v//./%{lua:os.execute('id')}}",
        "v=%{name}; echo ${v//-/%(cat /etc/passwd)}",
    ],
)
def test_bash_replace_rejects_unsafe_repl(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "body",
    [
        'test "a" == "a" && echo "%(whoami)" || echo "no"',
        'test "a" != "b" && echo "safe" || echo "%(id)"',
        'test "%(whoami)" == "a" && echo "yes" || echo "no"',
        'test "a" == "%(whoami)" && echo "yes" || echo "no"',
    ],
)
def test_test_str_rejects_unsafe_values(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "body",
    [
        '[ -z "%{?flag}" ] && echo "%(whoami)" || echo "safe"',
        '[ -z "%{?flag}" ] && echo "safe" || echo "%(whoami)"',
    ],
)
def test_test_empty_rejects_unsafe_values(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "body",
    [
        "date +%(whoami)",
        'date +"%(whoami)%Y"',
    ],
)
def test_date_rejects_unsafe_format(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "body",
    [
        "echo %{version} | sed 's/\\./ %(whoami)/g'",
        "echo %{version} | sed 's/x/%(id)/g'",
    ],
)
def test_sed_rejects_unsafe_replacement(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "body",
    [
        """echo %{version} | awk -F. '{print $1"%(whoami)"$2}'""",
    ],
)
def test_awk_rejects_unsafe_separator(body):
    assert Sanitizer.sanitize_shell_expansion(body) == "%{nil}"


@pytest.mark.parametrize(
    "code",
    [
        'print("\\037(whoami)")',
        'print("\\037{lua:os.execute(\\"id\\")}")',
        'print("\\x25(whoami)")',
        'print("\\u{25}(whoami)")',
        'print("\\037\\z (whoami)")',
    ],
)
def test_lua_unsafe_escape_sequence_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'print(string.format("%c(whoami)", 37))',
        'print(string.format("%c", 37) .. "(whoami)")',
    ],
)
def test_lua_unsafe_string_format_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'print(("%c(whoami)"):format(37))',
        'print((""):format(37))',
        'print((""):char(37))',
        'print((""):dump())',
    ],
)
def test_lua_unsafe_colon_method_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        'print("%" .. "(whoami)")',
        'print("x%" .. "(whoami)")',
        'print("\\037" .. "(whoami)")',
    ],
)
def test_lua_unsafe_concatenation_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        # string.sub can extract % from a string
        'print(string.sub("% ", 1, 1) .. "(whoami)")',
        # colon variant
        'print(("% "):sub(1, 1) .. "(whoami)")',
        # string.find can capture %
        'local _,_,c = string.find("% x", "^(.)"); print(c .. "(whoami)")',
        # string.reverse can rearrange
        'print(string.reverse("X%") .. "(whoami)")',
        # string.rep can reproduce
        'print(string.rep("% ", 1):sub(1,1) .. "(whoami)")',
    ],
)
def test_lua_unsafe_string_extraction_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        # Aliasing string.format to a variable bypasses format validation
        'local f=string.format print(f("%%%c(whoami)", 40))',
        'local f=string.format; print(f("%%%c", 40) .. "whoami)")',
        # Assigning to table field
        'local t={f=string.format} print(t.f("%%%c", 40))',
    ],
)
def test_lua_unsafe_string_format_alias_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


@pytest.mark.parametrize(
    "code",
    [
        # Comment injection: --[[ inside a string tricks regex-based comment stripping
        'x = "--[["; os.execute("id"); x = "--]]"',
        # Variant with single-line comment syntax
        "x = '--[['; os.execute('id'); x = '--]]'",
        # With level-1 long brackets
        'x = "--[=["; os.execute("id"); x = "--]=]"',
    ],
)
def test_lua_unsafe_comment_injection_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


def test_lua_safe_real_comment_not_confused_with_string():
    """Real comments should still be stripped correctly."""
    assert Sanitizer.is_lua_safe('print(rpm.expand("%{version}")) -- safe comment')
    assert Sanitizer.is_lua_safe("local x = 1 --[[ block comment ]] print(x)")


@pytest.mark.parametrize(
    "value, expected_sanitized",
    [
        ("%[1+1]", "%[1+1]"),
        ("%[%{version}]", "%[%{version}]"),
        (
            '%[%{lua:os.execute("id")}]',
            "%[%{nil}]",
        ),
        (
            "%[%(whoami)]",
            "%[%{nil}]",
        ),
        # lua: prefix in expression expansion (RPM 4.16+)
        ("%[lua:os.execute('id')]", "%{nil}"),
        ("%[lua: os.execute('id')]", "%{nil}"),
        # safe lua: expression
        (
            '%[lua:rpm.expand("%{version}")]',
            '%[lua:rpm.expand("%{version}")]',
        ),
    ],
)
def test_expression_expansion_sanitized(value, expected_sanitized):
    sanitized, _, _ = Sanitizer.sanitize(value)
    assert sanitized == expected_sanitized


@pytest.mark.parametrize(
    "value, expected_sanitized",
    [
        # EnclosedMacroSubstitution without args - unsafe name
        ("%{%(whoami)}", "%{%{nil}}"),
        # EnclosedMacroSubstitution with args - unsafe name
        ("%{%(whoami) arg1 arg2}", "%{%{nil} arg1 arg2}"),
        # BuiltinMacro - unsafe name
        ("%{%(whoami):body}", "%{nil}"),
        # BuiltinMacro - nested macro in name (splits at : giving unterminated name)
        ('%{%{lua:os.execute("id")}}', "%{nil}"),
        # ConditionalMacroExpansion - unsafe name
        ("%{?%(whoami):body}", "%{nil}"),
        ("%{!%(whoami):body}", "%{nil}"),
        # safe names pass through
        ("%{version}", "%{version}"),
        ("%{?dist}", "%{?dist}"),
        ("%{?prerel:0.}", "%{?prerel:0.}"),
    ],
)
def test_macro_name_sanitized(value, expected_sanitized):
    sanitized, _, _ = Sanitizer.sanitize(value)
    assert sanitized == expected_sanitized


@pytest.mark.parametrize(
    "code",
    [
        "print(rpm.expand(\"%[lua:os.execute('id')]\"))",
        'print("%[1+1]")',
    ],
)
def test_lua_unsafe_expression_expansion_in_string(code):
    assert not Sanitizer.is_lua_safe(code)


def test_sed_pattern_newline_escape():
    result = Sanitizer.sanitize_shell_expansion(r"echo %{desc} | sed -e 's/\n/ /g'")
    assert result is not None
    assert "\\n" in result


def test_sed_pattern_parentheses_escaped():
    result = Sanitizer.sanitize_shell_expansion("echo %{version} | sed -e 's/(dev)//g'")
    assert result is not None
    assert "%(" in result
    assert "%)" in result


def test_sanitize_idempotent_printf_float():
    """Sanitizing already-sanitized printf float output should not break it."""
    first_pass = Sanitizer.sanitize('%(LANG=C printf "%.4f" %{cpan_version})')[0]
    assert "string.format" in first_pass
    second_pass = Sanitizer.sanitize(first_pass)[0]
    assert "string.format" in second_pass
    assert second_pass == first_pass


@pytest.mark.parametrize(
    "code",
    [
        # \040 = ( in Lua decimal escape
        'rpm.expand("%\\040whoami)")',
        # \091 = [ , \058 = :
        "rpm.expand(\"%\\091lua\\058os.execute('id')\\093\")",
        # hex escapes for ( and {
        'rpm.expand("%\\x28whoami)")',
        "rpm.expand(\"%\\x7blua\\x3aos.execute('id')}\")",
        # unicode escapes
        'rpm.expand("%\\u{28}whoami)")',
    ],
)
def test_lua_unsafe_char_escape_bypass(code):
    assert not Sanitizer.is_lua_safe(code)


def test_decode_lua_escapes_out_of_range():
    """Decimal escapes > 255 are truncated to fit in a byte, matching Lua behavior."""
    # \293 decodes to chr(293 % 256) == chr(37) == '%', trailing '%' is unsafe
    assert not Sanitizer.is_lua_safe(r'print("\293")')
    # \300 decodes to chr(300 % 256) == chr(44) == ',', safe
    assert Sanitizer.is_lua_safe(r'print("\300")')
    # \256 and \512 decode to chr(0), safe
    assert Sanitizer.is_lua_safe(r'print("\256")')
    assert Sanitizer.is_lua_safe(r'print("\512")')


def test_sanitize_depth_limit():
    """Deeply nested macros hit the depth limit instead of RecursionError."""
    nested = "%{version}"
    for _ in range(100):
        nested = f"%{{expand:{nested}}}"
    sanitized, _, removed = Sanitizer.sanitize(nested)
    assert removed > 0
    assert "%{nil}" in sanitized
