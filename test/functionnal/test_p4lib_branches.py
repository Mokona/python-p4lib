#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 branches'."""

import os
import sys
import unittest
import pprint

import testsupport
from p4lib import P4, P4LibError


class BranchesTestCase(unittest.TestCase):
    def test_get_branches(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()

        try:
            os.chdir(andrew['home'])

            branch = {
                "branch": "test_get_branches",
                "description": "test_get_branches",
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branch)
            branches = p4.branches()
            for branch in branches:
                if branch["branch"] == "test_get_branches":
                    self.failUnless(branch.has_key('branch'))
                    self.failUnless(branch.has_key('update'))
                    self.failUnless(branch.has_key('description'))
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(BranchesTestCase)

