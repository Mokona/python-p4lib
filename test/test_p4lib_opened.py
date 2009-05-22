#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 opened'."""

import os
import sys
import unittest
import pprint

import testsupport
from p4lib import P4, P4LibError


class OpenedTestCase(unittest.TestCase):
    def test_none_opened(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])

            results = p4.opened()
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened('./...')
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(['./...'])
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(['//...'])
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(change='default')
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(change=123)
            self.failIf(results, "Unexpected results: %r" % results)

            self.failUnlessRaises(P4LibError, p4.opened, change='foo')
        finally:
            os.chdir(top)

    def test_none_opened_anywhere(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])

            results = p4.opened(allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened('./...', allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(['./...'], allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(['//...'], allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(change='default', allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)
            results = p4.opened(change=123, allClients=1)
            self.failIf(results, "Unexpected results: %r" % results)

            self.failUnlessRaises(P4LibError, p4.opened, change='foo',
                                  allClients=1)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(OpenedTestCase)

