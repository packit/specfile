#!/usr/bin/python3
from specfile import Specfile
import sys

# this is dump, but do the work
filename = sys.argv[1]
print("Parsing {}".format(filename))
specfile = Specfile(filename, force_parse=True)
