#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 branch'."""

import os
import sys
import unittest
import pprint

import testsupport
from p4lib import P4, P4LibError


class BranchTestCase(unittest.TestCase):
    #TODO:
    # - test expected error from trying to change a locked branch from a
    #   user that is not the owner
    # - have the super user change a locked branch with and without force
    def test_get_branch(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_get_branch"
            branchDict = {
                "branch": name,
                "description": name,
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branchDict)
            branch = p4.branch("test_get_branch")
            self.failUnless(branch["branch"] == name)
            self.failUnless("access" in branch)
            self.failUnless("description" in branch)
            self.failUnless("options" in branch)
            self.failUnless("owner" in branch)
            self.failUnless("update" in branch)
            self.failUnless("view" in branch)
        finally:
            os.chdir(top)

    def test_create_branch(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_create_branch"
            branchDict = {
                "branch": name,
                "description": name,
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branchDict)
            branches = p4.branches()
            for branch in branches:
                if branch["branch"] == name:
                    break
            else:
                self.fail("Branch '%s' not successfully created" % name)
        finally:
            os.chdir(top)

    def test_delete_branch(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_delete_branch"
            branchDict = {
                "branch": name,
                "description": name,
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branchDict)
            p4.branch(name=name, delete=1)

            branches = p4.branches()
            for branch in branches:
                if branch["branch"] == name:
                    self.fail("Branch '%s' was not successfully deleted"\
                              % name)
        finally:
            os.chdir(top)

    def test_update_branch(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_update_branch"
            descBefore = "before"
            descAfter = "after"

            # Create a branch and then update it.
            branchDict = {
                "branch": name,
                "description": descBefore,
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branchDict)
            p4.branch(name=name, branch={"description": descAfter})

            branch = p4.branch(name=name)
            self.failUnless(branch["description"] == descAfter)
        finally:
            os.chdir(top)

    def test_update_branch_no_change(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_update_branch_no_change"

            # Create a branch and then update it.
            branchDict = {
                "branch": name,
                "description": name,
                "view": "//depot/v1/... //depot/v2/...",
            }
            p4.branch(branch=branchDict)
            p4.branch(name=name, branch={})
            # Update the client.
            result = p4.branch(name=name, branch={})
            self.failUnless(result["branch"] == name)
            self.failUnless(result["action"] == "not changed")

        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(BranchTestCase)

