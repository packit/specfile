# specfile

Python library for parsing and manipulating RPM spec files. Main focus is on modifying existing spec files, any change should result in a minimal diff.

This project is still a work in progress.

## Motivation

Originally, [rebase-helper](https://github.com/rebase-helper/rebase-helper/) provided an API for spec file modifications that was also used by [packit](https://github.com/packit/packit). The goal of this project is to make the interface more general and convenient to use by not only packit but also by other Python projects that need to interact with RPM spec files.

## Important terms used in this library

### Section

Section is a spec file section, it has a well-defined name that starts with _%_ character and that can optionally be followed by arguments.

In this library, the starting _%_ of section name is ommited for convenience.

There is a special section internally called `%package`, often also referred to as preamble, and it represents the content of the spec file that preceeds the first named section (usually `%description`). This section contains the main package metadata (tags). Metadata of subpackages are defined in subsequent `%package` sections, that are not anonymous and are always followed by arguments specifying the name of the subpackage (e.g. `%package doc` or `%package -n completely-different-subpackage-name`).

### Tag

Tag represents a single item of metadata of a package. It has a well-defined name and a value. Tags are defined in `%package` sections.

For the purposes of this library, a tag can have associated comments. These are consecutive comment lines directly above the tag definition in a spec file.

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
    print(getattr(sections, 'package devel'))
    # inserting a line into a section
    sections.build.insert(0, 'export VERBOSE=1')

# copying a section from one specfile to another
with specfile1.sections() as sections1, with specfile2.sections() as sections2:
    sections2.changelog[:] = sections1.changelog
```

### Mid-level manipulation - tags and changelog

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

#### Changelog

```python
# adding a new entry, author is determined using rpmdev-packager (if available)
specfile.add_changelog_entry('New upstream release 2.1')

# adding a new entry, specifying author and timestamp explicitly
specfile.add_changelog_entry(
    'New upstream release 2.1',
    author='Nikola Forró',
    email='nforro@redhat.com',
    timestamp=datetime.date(2021, 11, 20),
)
```

#### Sources and patches

```python
print(specfile.sources)
print(specfile.patches)
print(specfile.sources[0].filename)
specfile.sources.append('tests.tar.gz')
specfile.patches[0] = 'downstream.patch'

# fetching non-local sources (including patches)
specfile.download_remote_sources()

# same thing, but trying to fetch from lookaside cache first
specfile.download_remote_sources(lookaside=True)
```

#### Other attributes

```python
print(specfile.url)
specfile.summary = '...'
```

## Caveats

### RPM macros

specfile uses RPM for parsing spec files and macro expansion. Unfortunately, macros are always stored in a global context, which poses a problem for multiple instances of Specfile.
