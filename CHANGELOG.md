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
