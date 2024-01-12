# specfile

specfile is a pure-Python library for parsing and manipulating RPM spec files.
Main focus is on modifying existing spec files, any change should result in a minimal diff.

## Installation

The library is packaged for Fedora, EPEL 9 and EPEL 8 and you can simply instal it with dnf:

```bash
dnf install python3-specfile
```

On other systems, you can use pip (just note that it requires RPM Python bindings to be installed):

```bash
pip install specfile
```
