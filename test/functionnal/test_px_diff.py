#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test px.py's interface to 'p4 diff'."""

import os
import sys
import unittest
import re
import pprint

import testsupport
from p4lib import P4, P4LibError


class DiffTestCase(unittest.TestCase):
    def test_list_new_files(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_list_new_files.txt'

        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            argv = ['px', 'diff', '-sn', './...']
            output, error, retval = testsupport.run(argv)

            files = [f[:-1] for f in output] # drop newlines
            self.failUnless(os.path.abspath(fname) in files)
            self.failIf(error)
            self.failIf(retval)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_same_as_p4_1(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_same_as_p4_1.txt'

        try:
            os.chdir(andrew['home'])
            
            # Make first version of a file.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "for test_same_as_p4_1")

            # Make an edit to be able to compare the diffs.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            
            pxArgv = ['px', 'diff', '-du', './...']
            pxOutput, pxError, pxRetval = testsupport.run(pxArgv)
            p4Argv = ['p4', 'diff', '-du', './...']
            p4Output, p4Error, p4Retval = testsupport.run(p4Argv)

            self.failUnless(pxOutput == p4Output,
                "Output from running %s was not the same as %s. This %r "\
                "vs this %r." % (pxArgv, p4Argv, pxOutput, p4Output))
            self.failUnless(pxError == p4Error,
                "Error from running %s was not the same as %s. This %r "\
                "vs this %r." % (pxArgv, p4Argv, pxError, p4Error))
            self.failUnless(pxRetval == p4Retval,
                "Retval from running %s was not the same as %s. This %r "\
                "vs this %r." % (pxArgv, p4Argv, pxRetval, p4Retval))

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(DiffTestCase)

