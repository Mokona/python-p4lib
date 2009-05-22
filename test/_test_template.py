#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 foo'."""

import os
import sys
import unittest
import pprint
import testsupport
from p4lib import P4, P4LibError

class FooTestCase(unittest.TestCase):
    def test_something_as_andrew(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # play with p4lib ...
        finally:
            os.chdir(top)

    def test_something_as_bertha(self):
        top = os.getcwd()
        bertha = testsupport.users['bertha']
        try:
            os.chdir(bertha['home'])
            # play with p4lib ...
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(FooTestCase)

