#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 submit'."""

import os
import unittest

import testsupport
from p4lib import P4


class SubmitTestCase(unittest.TestCase):
    #TODO:
    # - test more submit output lines (try to get all possible syntaxes)
    # - test failed submissions
    # - test with implicit file list

    def test_submit_simple(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_submit_simple.txt'
            with open(fname, 'w') as f:
                f.write('Hello there.\n')
            p4.add(fname)
            result = p4.submit(fname, 'first checkin of this file')
            self.failUnless(result['action'] == 'submitted')
            self.failUnless('change' in result)
            self.failUnless(result['files'][0]['depotFile']
                            == p4.where(fname)[0]['depotFile'])
            self.failUnless(result['files'][0]['rev'] == 1)
            self.failUnless(result['files'][0]['action'] == 'add')
        finally:
            os.chdir(top)

    def test_submit_implicit_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_submit_implicit_files.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            result = p4.submit([], 'checkin with implicit files')
            self.failUnless(result['action'] == 'submitted')
            self.failUnless(result.has_key('change'))

            actual = result['files'][0]['depotFile']
            expected = p4.where(fname)[0]['depotFile']
            self.failUnless(actual == expected,
                            "%r != %r" % (actual, expected))
        finally:
            os.chdir(top)

    def test_submit_pending_changelist(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_submit_pending_changelist.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            c = p4.change([fname], 'my pending change')
            cnum = c['change']
            result = p4.submit(change=cnum)
            self.failUnless(result['action'] == 'submitted')
            self.failUnless(result['files'][0]['depotFile']\
                            == p4.where(fname)[0]['depotFile'])
            self.failUnless(result['files'][0]['action'] == 'add')
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(SubmitTestCase)

