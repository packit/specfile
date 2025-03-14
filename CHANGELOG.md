# 0.34.2

- context_management: add a type stub override to fix typing. Type checkers like mypy and pyright can now correctly determine the types for `.sources()`, `.sections()`, and the other `Specfile` methods that return context managers. (#457)

# 0.34.1

- Removed the usage of a walrus operator for Python 3.6 compatibility. (#450)

# 0.34.0

- Added support for detached (open)SUSE style changelogs (#444)

# 0.33.0

- There is a new convenience method `Sections.get_or_create()` that allows you to manipulate a section
  without checking if it exists first. If a section doesn't exist, it will be appended to the end. (#441)
  For example, this will work properly even on spec files without `%changelog`:

        with spec.sections() as sections:
            changelog = sections.get_or_create("changelog")
            changelog[:] = ["%autochangelog"]

# 0.32.6

- New minor release for testing in CBS Koji

# 0.32.5

- We have fixed our parser to take in account the deprecations introduced in Python 3.8 (#420)

# 0.32.4

- NEVR and NEVRA classes are now hashable (#416)

# 0.32.3

- specfile can now handle multi-line tag values (enclosed in a macro body, e.g. `%shrink`). (#412)

# 0.32.2

- Explicitly invalidate the global parse hash when a SpecParser instance is created to prevent this issue. (#409)

# 0.32.1

- Fixed two issues related to condition parsing. (#405)

# 0.32.0

- It is now possible to bump a release in a manner similar to `rpmdev-bumpspec` using `Specfile.bump_release()` method. (#399)

# 0.31.0

- Value of a `Tag` no longer includes trailing whitespace (if any). (#393)
- specfile now tries to expand macros before processing conditions to be able to resolve conditional expressions defined by macros, for example OpenSUSE Tumbleweed defines `%ifpython3` macro as `%if "%{python_flavor}" == "python3"`. (#394)

# 0.30.0

- Fixed an exception that occured when accessing the `Specfile.has_autochangelog` property while having unparseable lines (e.g. lines ending with unescaped `%`) in `%changelog`. (#387)

# 0.29.0

- Improved compatibility with RPM 4.20 (alpha version is currently in Fedora Rawhide). (#380)

# 0.28.3

- Fixed several minor issues such as processing seemingly commented-out macro definitions (e.g. `#%global prerel rc1`) and treating `SourceLicense` tag as a source. (#374, #376)
- Made `EVR`, `NEVR` and `NEVRA` objects comparable. (#379)

# 0.28.2

- Handling of trailing newlines in the macro defintions has been improved. (#361)

# 0.28.1

- We have fixed an issue in `%prep` section processing. For instance, if the `%patches` macro appeared there, it would have been converted to `%patch es`, causing failure when executing `%prep` later. (#356)

# 0.28.0

- A trailing newline is no longer added to spec files without one upon saving. (#353)

# 0.27.0

- Improved handling of commented-out macro definitions and fixed related logic in `Specfile.update_value()`. (#338)

# 0.26.0

- When accessing tags or macro definitions by name, specfile now takes validity into account when looking for the best match. For example if there are two instances of `Version` tag, one in the true and one in the false branch of a condition, `Specfile.version` will always access the one that is in the true branch. (#328)

# 0.25.1rc1

- Third pre-release for testing Packit support.

# 0.25.0

- There is a new method, `Specfile.update_version()`, that allows updating spec file version even if it is a pre-release. (#317)

# 0.24.1rc2

- Second pre-release for testing Packit support.

# 0.24.1-rc1

- First pre-release for testing Packit support.

# 0.24.0

- Improved type annotations for `UserList` subclasses. (#299)
- Macro definitions gained a new `commented_out` property indicating that a macro definition is commented out. Another new property, `comment_out_style`, determines if it is achieved by using a `%dnl` (discard next line) directive (e.g. `%dnl %global prerelease beta2`) or by replacing the starting `%` with `#` (e.g. `#global prerelease beta2`). (#298)

# 0.23.0

- Sources now have a `valid` property that indicates whether a source is valid in the current context, meaning it is not present in a false branch of any condition. (#295)

# 0.22.1

- Removed dependency on setuptools-scm-git-archive. (#290)

# 0.22.0

- Macro definitions and tags gained a new `valid` attribute. A macro definition/tag is considered valid if it doesn't appear in a false branch of any condition appearing in the spec file. (#276)

# 0.21.0

- `specfile` no longer tracebacks when some sources are missing and can't be _emulated_. In such case the spec file is parsed without them at the cost of `%setup` and `%patch` macros potentially expanding differently than with the sources present. (#271)
- Specfile's license in RPM spec file is now confirmed to be SPDX compatible. (#269)

# 0.20.2

- Fixed Packit config to work properly with `propose-downstream` and `pull-from-upstream` jobs. (#261)

# 0.20.1

- specfile now once again supports EPEL 8 and Python 3.6. (#256)

# 0.20.0

- Fixed infinite loop when removing macros with `%` in the name. (#244)
- Added a possibility to undefine system macros by setting a macro value to `None` in the `macros` argument of the `Specfile` constructor. (#244)
- Fixed a bug in processing options of `%prep` macros. For instance, when a quoted string appeared inside an expression expansion, it could lead to improper parsing, rendering the spec file invalid after accessing the options. (#253)

# 0.19.0

- Parsing has been optimized so that even spec files with hundreds of thousands of lines can be processed in reasonable time. (#240)

# 0.18.0

- Specfile library now handles multiple `%changelog` sections. (#230)

# 0.17.0

- Added a new `guess_packager()` function that uses similar heuristics as `rpmdev-packager`, meaning that the `Specfile.add_changelog_entry()` method no longer requires `rpmdev-packager` to guess the changelog entry author. (#220)
- The `Specfile.add_changelog_entry()` method now uses dates based on UTC instead of the local timezone. (#223)

# 0.16.0

- Added `Specfile.has_autorelease` property to detect if a spec file uses the `%autorelease` macro. (#221)

# 0.15.0

- Parsing the spec file by RPM is now performed only if really necessary, greatly improving performance in certain scenarios. (#212)
- Checked that license is a valid SPDX license.

# 0.14.0

- Fixed a bug that broke parsing in case spec file contained conditionalized macro definitions or similar constructs. (#209)
- Specfile no longer depends on rpm-py-installer, it now depends directly on rpm. (#207)

# 0.13.2

- Fixed infinite loop that occured when section options were followed by whitespace. (#197)

# 0.13.1

- Fixed a bug in section parsing that caused sections to be ignored when there were macro definitions spread across the spec file and not cumulated at the top. (#191)

# 0.13.0

- Added `Section.options` attribute for convenient manipulation of section options. (#183)
- specfile now supports single-line sections where section content is represented by a macro starting with a newline. (#182)
- Added `evr` argument to `Specfile.add_changelog_entry()`. This allows adding a changelog entry with an EVR value that's different from the current specfile's value. This makes it easier to reconstruct a specfile's `%changelog` based on another source using the higher level interface. (#181)

# 0.12.0

- All classes including `Specfile` itself can now be copied using the standard `copy()` and `deepcopy()` functions from `copy` module. (#176)
- `Section.name` attribute has been renamed to a more fitting `Section.id`. (#167)
- `setup.cfg` now uses `license_files` instead of deprecated `license_file`. (#162)

# 0.11.1

- Tags enclosed in conditional macro expansions are not ignored anymore. (#156)
- Fixed context managers being shared between Specfile instances. (#157)

# 0.11.0

- Context managers (`Specfile.sections()`, `Specfile.tags()` etc.) can now be nested and combined together (with one exception - `Specfile.macro_definitions()`), and it is also possible to use tag properties (e.g. `Specfile.version`, `Specfile.license`) inside them. It is also possible to access the data directly, avoiding the `with` statement, by using the `content` property (e.g. `Specfile.tags().content`), but be aware that no modifications done to such data will be preserved. You must use `with` to make changes. (#153)

# 0.10.0

- Fixed an issue that caused empty lines originally inside changelog entries to appear at the end. (#140)
- Renamed the `ignore_missing_includes` option to a more general `force_parse`. If specified, it allows to attempt to parse the spec file even if one or more sources required to be present at parsing time are not available. Such sources include sources referenced from shell expansions in tag values and sources included using the `%include` directive. (#137)

# 0.9.1

- `specfile` now supports localized tags (e.g. `Summary(fr)`) and tags with qualifiers (e.g. `Requires(post)`).
  It also follows more closely rpm parsing logic and doesn't fail on invalid section names. (#132)

# 0.9.0

- Added utility classes for working with (N)EVR. (#113)
- Fixed an issue with multiple instances of `Specfile` not expanding macros in the right context. (#117)

# 0.8.0

- Added `Specfile.update_tag()` method that allows updating tag values while trying to preserve macro expansions. You can watch a demo on [YouTube](https://youtu.be/yzMfBPdFXZY). (#101)

# 0.7.0

- It is now possible to filter changelog entries by specifying lower bound EVR, upper bound EVR or both. (#104)
- Added support for filenames specified in source URL fragments, for example: `https://example.com/foo/1.0/download.cgi#/%{name}-%{version}.tar.gz` (#100)

# 0.6.0

- Switched to our own implementation of working with `%changelog` timestamps and removed dependency on arrow (#88)
- Fixed requires of EPEL 8 rpm (#86)

# 0.5.1

- Added new `%conf` section (#74)
- Switched to rpm-py-installer (#75)
- Fixed detecting extended timestamp format in `%changelog` (#77, #81)

# 0.5.0

- Strict optional typing is now enforced (#68)
- Fixed deduplication of tag names (#69)
- Sources and patches can now be removed by number (#69)
- Number of digits in a source number is now expressed the same way as packit does it (#69)
- Empty lines are now compressed when deleting tags (#69)
- Added convenience property for getting texts of tag comments (#69)
- Added convenience method for adding a patch (#69)

# 0.4.0

- Added convenience properties for most used tags (#63)
- Hardened linting by ignoring only specific mypy errors (#64)
- Fixed list of valid tag names and ensured newly added tags are not part of a condition block (#66)
- Initial patch number and its default number of digits are now honored (#66)
- Fixed a bug in `%prep` macro stringification (#67)

# 0.3.0

- Made `Sources` a `MutableSequence` (#36)
- Started using consistent terminology for source numbers and added the option to insert a source with a specific number (#47)
- Added support for implicit source numbering (#48)
- Documented sources and `%prep` macros in README (#49)
- Implemented high-level manipulation of version and release (#54)
- Added support for `%autochangelog` (#56)
- Added `remote` property to sources and enabled addition of `Sources` (#59)
- Implemented mid-level manipulation of `%prep` section, including modification of `%prep` macros (#37, #52)

# 0.2.0

- Enabled Zuul CI (#8)
- Switched from git:// to https:// for rebase hook (#22)
- Updated pre-commit configuration and adapted to type changes brought by new version of mypy (#24)
- Non-lowercase section names are now supported (#26)
- Added `Sections.get()` convenience method (#29)
- Added packit configuration and enabled packit (#25)
- Fixed infinite recursion when deep-copying instances of `Sections` and `Tags` (#30)
- Updated Fedora and EPEL spec files (#32)
- Fixed issues caused by older versions of dependencies on EPEL 8 (#33)
- Implemented high-level manipulation of sources and patches (#20, #36)
- It is now possible to parse spec files with missing local sources (#23)

# 0.1.1

- Fixed parsing _Source_ and _Patch_ tags
- Made `Specfile` importable directly from the package
