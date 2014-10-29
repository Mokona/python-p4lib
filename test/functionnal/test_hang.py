#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Ensure that we cannot get p4 to hang."""

import os
import sys
import unittest
import types
import pprint

import testsupport
from p4lib import P4, P4LibError


class HangTestCase(unittest.TestCase):
    def test_hang_long_local_path_with_asterisk(self):
        # Usage in Komodo turned up occassional hangs of p4 on Windows when
        # called, for example, p4 have, p4 files, and p4 opened in quick
        # succession on a long local path name with an asterisk, e.g.:
        #   D:\trentm\as\Apps\Komodo-devel\src\chrome\komodo\content\doc\komodo/*
        # The number of characters seemed to be a factor. Hypothesis:
        #   - The actual command launched via p4lib's usage of os.popen3
        #     is 'cmd /c "p4 have D:\trentm\.../*"'.
        #   - Cmd is globbing the * (even though it advertises that it does
        #     NOT do this) and if the globbed result is too many characters
        #     (lots of files and long filenames) then the command ends up
        #     hanging.
        # The fix:
        #   - Ensure the command is:
        #       cmd /c "p4 have "D:\trentm\.../*""
        #     so cmd.exe know not to play with the filename argument.
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            
            dname = os.path.join("this", "is", "a", "really", "really",
                                 "really", "really", "really", "really", 
                                 "really", "really", "really", "really", 
                                 "really", "really", "really", "really", 
                                 "long", "path", "name", "to", "my", "files")
            os.makedirs(dname)

            for i in range(1):
                fname = os.path.join(dname,
                    "test_hang_long_local_path_with_asterisk_%d.txt" % i)
                fout = open(fname, 'w')
                fout.write('Hello there.\n')
                fout.close()
                p4.add(fname)
                p4.submit(fname, "for hang test")

            for i in range(100):
                f = os.path.join(dname, "foobar%d.txt" % i)
                fout = open(f, 'w')
                fout.write("foobar\n")
                fout.close()

            arg = dname + "/*"
            p4.have(arg)
            p4.files(arg)
            p4.opened(arg)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(HangTestCase)

