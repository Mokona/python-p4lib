#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 label'."""

import os
import unittest

import testsupport
from p4lib import P4


class LabelTestCase(unittest.TestCase):
    #TODO:
    # - test expected error from trying to change a locked label from a
    #   user that is not the owner
    # - have the super user change a locked label with and without force
    def test_get_label(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_get_label"
            labelDict = {
                "label": name,
                "description": name,
                "view": "//depot/...",
            }
            p4.label(label=labelDict)
            label = p4.label("test_get_label")
            self.failUnless(label["label"] == name)
            self.failUnless("access" in label)
            self.failUnless("description" in label)
            self.failUnless("options" in label)
            self.failUnless("owner" in label)
            self.failUnless("update" in label)
            self.failUnless("view" in label)
        finally:
            os.chdir(top)

    def test_create_label(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_create_label"
            labelDict = {
                "label": name,
                "description": name,
                "view": "//depot/...",
            }
            p4.label(label=labelDict)
            labels = p4.labels()
            for label in labels:
                if label["label"] == name:
                    break
            else:
                self.fail("Label '%s' not successfully created" % name)
        finally:
            os.chdir(top)

    def test_delete_label(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_delete_label"
            labelDict = {
                "label": name,
                "description": name,
                "view": "//depot/...",
            }
            p4.label(label=labelDict)
            p4.label(name=name, delete=1)

            labels = p4.labels()
            for label in labels:
                if label["label"] == name:
                    self.fail("Label '%s' was not successfully deleted" % name)
        finally:
            os.chdir(top)

    def test_update_label(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_update_label"
            descBefore = "before"
            descAfter = "after"

            # Create a label and then update it.
            labelDict = {
                "label": name,
                "description": descBefore,
                "view": "//depot/...",
            }
            p4.label(label=labelDict)
            p4.label(name=name, label={"description": descAfter})

            label = p4.label(name=name)
            self.failUnless(label["description"] == descAfter)
        finally:
            os.chdir(top)

    def test_update_label_no_change(self):
        top = os.getcwd()
        andrew = testsupport.users["andrew"]
        p4 = P4()

        try:
            os.chdir(andrew["home"])

            name = "test_update_label_no_change"

            # Create a label and then update it.
            labelDict = {
                "label": name,
                "description": name,
                "view": "//depot/...",
            }
            p4.label(label=labelDict)
            p4.label(name=name, label={})
            # Update the client.
            result = p4.label(name=name, label={})
            self.failUnless(result["label"] == name)
            self.failUnless(result["action"] == "not changed")

        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(LabelTestCase)

