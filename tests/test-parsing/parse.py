#!/usr/bin/python3
import sys

from specfile import Specfile

# this is dump, but do the work
filename = sys.argv[1]
print("Parsing {}".format(filename))
specfile = Specfile(filename, force_parse=True)
