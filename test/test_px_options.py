#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test px.py's interface to 'p4 backout'."""

import os
import sys
import unittest
import re
import pprint
import types

import testsupport
from p4lib import P4, P4LibError


class PxOptionsTestCase(unittest.TestCase):
    def test_h(self):
        argv = ['px', '-h']
        output, error, retval = testsupport.run(argv)
        landmark = "px Options:"
        for line in output:
            if line.strip().startswith(landmark):
                break
        else:
            self.fail("No '%s' line in output of %s." % (landmark, argv))

    def test_help(self):
        argv = ['px', '--help']
        output, error, retval = testsupport.run(argv)
        landmark = "px Options:"
        for line in output:
            if line.strip().startswith(landmark):
                break
        else:
            self.fail("No '%s' line in output of %s." % (landmark, argv))

    def test_V(self):
        argv = ['px', '-V']
        output, error, retval = testsupport.run(argv)
        landmarkRe = re.compile("px \d\.\d\.\d")
        match = landmarkRe.search(output[0])
        self.failUnless(match, "Could not find '%s' in first output line "\
                               "of %s: %r"\
                               % (landmarkRe.pattern, argv, output))

    def test_version(self):
        argv = ['px', '--version']
        output, error, retval = testsupport.run(argv)
        landmarkRe = re.compile("px \d\.\d\.\d")
        match = landmarkRe.search(output[0])
        self.failUnless(match, "Could not find '%s' in first output line "\
                               "of %s: %r"\
                               % (landmarkRe.pattern, argv, output))

    def test_g(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_g.txt'

        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            argv = ['px', '-g', 'opened', fname]
            output, error, retval = testsupport.run(argv)
            result = eval(''.join(output))
            self.failUnless(type(result) == types.DictType)
            opened = p4.opened(fname)[0]
            self.failUnless(result['change'] == opened['change'])
            self.failUnless(result['depotFile'] == opened['depotFile'])
            self.failUnless(result['type'] == opened['type'])
            self.failUnless(int(result['rev']) == int(opened['rev']))

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

##        print
##        print "-"*60, "output"
##        print output
##        print "-"*60, "error"
##        print error
##        print "-"*60, "retval"
##        print retval
##        print "-"*60

def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(PxOptionsTestCase)

