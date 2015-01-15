#!/usr/bin/env python
# See LICENSE.txt for license details.

import os
import unittest

import testsupport
from p4lib import _call_subprocess


class SubprocessTestCase(unittest.TestCase):
    def test_removes_and_restores_pwd_environment(self):
        if 'PWD' not in os.environ:
            os.environ['PWD'] = 'marker_for_test'
            pwd_was_set = True
        else:
            pwd_was_set = False

        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])


            old_pwd = os.environ['PWD']

            output, error, retval = _call_subprocess(['p4'])

            self.assertEqual(old_pwd, os.environ['PWD'])

        finally:
            if pwd_was_set:
                del os.environ['PWD']
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(SubprocessTestCase)
