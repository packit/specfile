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
