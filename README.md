# specfile

Python library for parsing and manipulating RPM spec files. Main focus is on modifying existing spec files, any change should result in a minimal diff.

## Motivation

Originally, [rebase-helper](https://github.com/rebase-helper/rebase-helper/) provided an API for spec file modifications that was also used by [packit](https://github.com/packit/packit). The goal of this project is to make the interface more general and convenient to use by not only packit but also by other Python projects that need to interact with RPM spec files.

## Important terms used in this library

### Section

Section is a spec file section, it has a well-defined name that starts with _%_ character and that can optionally be followed by arguments.

In this library, the starting _%_ of section name is omitted for convenience.

There is a special section internally called `%package`, often also referred to as preamble, and it represents the content of the spec file that precedes the first named section (usually `%description`). This section contains the main package metadata (tags). Metadata of subpackages are defined in subsequent `%package` sections, that are not anonymous and are always followed by arguments specifying the name of the subpackage (e.g. `%package doc` or `%package -n completely-different-subpackage-name`).

### Tag

Tag represents a single item of metadata of a package. It has a well-defined name and a value. Tags are defined in `%package` sections.

For the purposes of this library, a tag can have associated comments. These are consecutive comment lines directly above the tag definition in a spec file.

### Source

Source is a source file or a downstream patch defined by a `Source`/`Patch` tag or by an entry in `%sourcelist`/`%patchlist` section.

Source can be local, specified by a filename, or remote, specified by a URL. Local sources should be located in a directory referred to as `sourcedir`. Remote sources should be downloaded to this directory.

Sources defined by tags can be explicitly numbered, e.g. `Source0` or `Patch999`, otherwise implicit numbering takes place and source numbers are auto-assigned in a sequential manner.

### Prep macros

Prep macros are macros that often appear in (and only in, they don't make sense anywhere else) `%prep` section.

4 such macros are recognized by this library, [`%setup`](https://rpm-packaging-guide.github.io/#setup), [`%patch`](http://ftp.rpm.org/max-rpm/s1-rpm-inside-macros.html#S2-RPM-INSIDE-PATCH-MACRO), [`%autosetup`](https://rpm-software-management.github.io/rpm/manual/autosetup.html#autosetup-description) and [`%autopatch`](https://rpm-software-management.github.io/rpm/manual/autosetup.html#autopatch). A typical spec file uses either `%autosetup` or a combination of `%setup` and `%patch` or `%autopatch`.

## Documentation

[Full documentation generated from code](https://packit.dev/specfile/api/specfile).

## Examples and use cases

The following examples should cover use cases required by [packit](https://github.com/packit/research/blob/main/specfile/README.md).

### Instantiating

```python
from specfile import Specfile

# using an absolute path
specfile = Specfile('/tmp/test.spec')

# using a relative path and a different sourcedir
specfile = Specfile('test.spec', sourcedir='/tmp/sources')
```

### Reloading

```python
# if the spec file happens to be modified externally, it can be reloaded
specfile.reload()
```

### Saving changes

```python
# no autosave
specfile = Specfile('test.spec')
...
# saving explicitly when needed
specfile.save()

# enabling autosave, changes are saved immediately after any modification
specfile = Specfile('test.spec', autosave=True)

# as a context manager, saving is performed at context exit
with Specfile('test.spec') as specfile:
    ...
```

### Defining and undefining macros

```python
# override macros loaded from system macro files
specfile = Specfile('test.spec', macros=[('fedora', '38'), ('dist', '.fc38')])

# undefine a system macro (in case it's defined)
specfile = Specfile('test.spec', macros=[('rhel', None)])
```

### Low-level manipulation

```python
with specfile.sections() as sections:
    # replacing the content of a section
    sections.prep = ['%autosetup -p1']
    # removing a section
    del sections.changelog
    # swapping two sections
    sections[1], sections[2] = sections[2], sections[1]
    # accessing a section with arguments
    print(sections.get('package devel'))
    # inserting a line into a section
    sections.build.insert(0, 'export VERBOSE=1')

# copying a section from one specfile to another
with specfile1.sections() as sections1, with specfile2.sections() as sections2:
    sections2.changelog[:] = sections1.changelog
```

### Mid-level manipulation - tags, changelog and prep

```python
# accessing tags in preamble
with specfile.tags() as tags:
    # name of the first tag
    print(tags[0].name)
    # raw value of the first tag
    print(tags[0].value)
    # expanded value of the first tag
    print(tags[0].expanded_value)
    # comments associated with the first tag
    print(tags[0].comments)
    # value of a tag by name
    print(tags.url)
    tags.url = 'https://example.com'

# accessing tags in subpackages
with specfile.tags('package devel') as tags:
    print(tags.requires)

# working with changelog
with specfile.changelog() as changelog:
    # most recent changelog entry
    print(changelog[-1])
    # making changes
    changelog[1].content.append('- another line')
    # removing the oldest entry
    del changelog[0]

# working with macros in %prep section, supports %setup, %patch, %autosetup and %autopatch
from specfile.prep import AutosetupMacro

with specfile.prep() as prep:
    # name of the first macro
    print(prep.macros[0].name)
    # checking if %autosetup is being used
    print('%autosetup' in prep)
    print(AutosetupMacro in prep)
    # changing macro options
    prep.autosetup.options.n = '%{srcname}-%{version}'
    # adding a new %patch macro
    prep.add_patch_macro(28, p=1, b='.test')
    # removing an existing %patch macro by name
    del prep.patch0
    # this works for both '%patch0' and '%patch -P0'
    prep.remove_patch_macro(0)
```

### High-level manipulation

#### Version and release

```python
# getting version and release
print(specfile.version)
print(specfile.release)

# setting version and release
specfile.version = '2.1'
specfile.release = '3'

# setting both at the same time (release defaults to 1)
specfile.set_version_and_release('2.1', release='3')

# setting version while trying to preserve macros
specfile.set_version_and_release('2.1', preserve_macros=True)
```

#### Bumping release

To bump release and add a new changelog entry, you could use the following code:

```python
from specfile import Specfile

with Specfile("example.spec") as spec:
    spec.release = str(int(spec.expanded_release) + 1)
    spec.add_changelog_entry("- Bumped release for test purposes")
```

#### Changelog

```python
# adding a new entry, author is automatically determined
# (using the same heuristics that rpmdev-packager uses) if possible
# this function already honors autochangelog
specfile.add_changelog_entry('- New upstream release 2.1')

# adding a new entry, specifying author and timestamp explicitly
specfile.add_changelog_entry(
    '- New upstream release 2.1',
    author='Nikola Forró',
    email='nforro@redhat.com',
    timestamp=datetime.date(2021, 11, 20),
)

if specfile.has_autochangelog:
    # do something
```

#### Sources and patches

```python
with specfile.sources() as sources:
    # expanded location of the first source
    print(sources[0].expanded_location)
    # adding a source
    sources.append('tests.tar.gz')

with specfile.patches() as patches:
    # modifying location of the first patch
    patches[0].location = 'downstream.patch'
    # removing comments associated with the last patch
    patches[-1].comments.clear()
    # adding and removing patches
    patches.append('another.patch')
    del patches[2]
    # inserting a patch with a specific number
    patches.insert_numbered(999, 'final.patch')

# adding a single patch
specfile.add_patch('necessary.patch', comment='a human-friendly comment to the patch')
```

#### Other attributes

```python
print(specfile.name)
print(specfile.license)
print(specfile.summary)
specfile.url = 'https://example.com'
```

Note that if you want to access multiple tag values, it may be noticeably faster to do it using the `tags` context manager:

```python
# same as above, but roughly 4x times faster (parsing/saving happens only once)
with specfile.tags() as tags:
    print(tags.name.value)
    print(tags.license.value)
    print(tags.summary.value)
    tags.url.value = 'https://example.com'
```

### Read-only access

If you don't need write access, you can use the `content` property of context managers and avoid the `with` statement:

```python
# no changes done to the tags object will be saved
tags = specfile.tags().content

print(tags.version.expanded_value)
print(tags.release.expanded_value)

# number of sources
print(len(specfile.sources().content))
```

### Validity

Macro definitions, tags, `%sourcelist`/`%patchlist` entries and sources/patches have a `valid` attribute. An entity is considered valid if it isn't present in a false branch of any condition.

Consider the following in a spec file:

```specfile
%if 0%{?fedora} >= 36
Recommends: %{name}-selinux
%endif
```

Provided there are no other `Recommends` tags, the following would print `True` or `False` depending on the value of the `%fedora` macro:

```python
with specfile.tags() as tags:
    print(tags.recommends.valid)
```

You can define macros or redefine/undefine system macros using the `macros` argument of the constructor or by modifying the `macros` attribute of a `Specfile` instance.

The same applies to `%ifarch`/`%ifos` statements:

```specfile
%ifarch %{java_arches}
BuildRequires: java-devel
%endif
```

Provided there are no other `BuildRequires` tags, the following would print `True` in case the current platform was part of `%java_arches`:

```python
with specfile.tags() as tags:
    print(tags.buildrequires.valid)
```

To override this, you would have to redefine the `%_target_cpu` system macro (or `%_target_os` in case of `%ifos`).

## Videos

Here is a demo showcasing the `Specfile.update_tag()` method and its use cases:

[![Demo of Specfile.update_tag() functionality](https://img.youtube.com/vi/yzMfBPdFXZY/0.jpg)](https://www.youtube.com/watch?v=yzMfBPdFXZY)
