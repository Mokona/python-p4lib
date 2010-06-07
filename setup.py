#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Distutils setup script for px (and p4lib.py)."""

import sys
import os
from distutils.core import setup


#---- support routines

def _getVersion():
    from os.path import join, dirname
    sys.path.insert(0, join(dirname(__file__), "lib"))
    import p4lib
    return p4lib.__version__

def _getBinDir():
    """Return the current Python's bindir."""
    if sys.platform.startswith("win"):
        bindir = sys.prefix
    else:
        bindir = os.path.join(sys.prefix, "bin")
    return bindir


#---- setup mainline

if sys.platform.startswith('win'):
    scripts = []
    binFiles = ["px.exe", "px.py"]
else:
    scripts = ["px"]
    binFiles = []

setup(name="px",
      version=_getVersion(),
      description="Perforce 'p4' wrapper and Python interface",
      author="Trent Mick",
      author_email="TrentM@ActiveState.com",
      url="http://trentm.com/projects/px/",
      license="MIT License",
      platforms=["Windows", "Linux", "Mac OS X", "Unix"],
      long_description="""\
'px' is a wrapper command line app around the Perforce command line
client application 'p4'. It provides a light shim around the full
functionality of 'p4', extending some commands and adding others.

'p4lib.py' is a Python inteface for the Perforce command line client. It
is used by 'px', but is very usable directly for scripts that need to
talk to a Perforce repository.
""",
      keywords=["Perforce", "p4", "px"],

      py_modules=["p4lib"],
      scripts=scripts,
      data_files=[ (_getBinDir(), binFiles) ],
     )

