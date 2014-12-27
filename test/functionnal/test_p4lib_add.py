#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 add'."""

import os
import unittest
import types

import testsupport
from p4lib import P4


class AddTestCase(unittest.TestCase):
    def test_simple_add(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            newfile = 'hello.txt'
            open(newfile, 'w').write('Hello there.\n')
            result = p4.add(newfile)[0]
            self.failUnless(len(result))
            self.failUnless('depotFile' in result)
            self.failUnless('rev' in result)
            self.failUnless(type(result['rev']) == types.IntType)
            self.failUnless('comment' in result)
            opened = p4.opened(newfile)
            self.failUnless(len(opened) == 1,
                            "Added '%s', but it is not opened." % newfile)
            p4.revert(newfile)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(AddTestCase)

