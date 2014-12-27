#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 labels'."""

import os
import unittest

import testsupport
from p4lib import P4


class LabelsTestCase(unittest.TestCase):
    def test_get_labels(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()

        try:
            os.chdir(andrew['home'])

            label = {
                "label": "test_get_labels",
                "description": "test_get_labels",
                "view": "//depot/...",
            }
            p4.label(label=label)
            labels = p4.labels()
            for label in labels:
                if label["label"] == "test_get_labels":
                    self.failUnless('label' in label)
                    self.failUnless('update' in label)
                    self.failUnless('description' in label)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(LabelsTestCase)

