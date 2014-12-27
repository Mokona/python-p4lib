#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 resolve'."""

import os
import unittest

import testsupport
from p4lib import P4


class ResolveTestCase(unittest.TestCase):
    #TODO:
    #   - test resolves conflicts
    #   - test the other resolve options (force, verbose, text, dryrun)
    #   - test other 'autoMode' values
    #   - test resolve with no resolve necessary
    def test_resolve_no_conflict(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        bertha = testsupport.users['bertha']
        fname = 'test_resolve_no_conflict.txt'

        # Andrew creates a file and submits it and starts working on a
        # second revision of it.
        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10):
                fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'first checkin of this file')
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write('line 10\n')
            fout.close()
        finally:
            os.chdir(top)

        # Bertha syncs the first rev of the file and then submits a
        # non-conflicting edit to it.
        try:
            os.chdir(bertha['home'])
            p4.sync(fname)
            p4.edit(fname)
            contents = open(fname, 'r').readlines()
            contents[0] = contents[0][:-1] + ' (bertha was here)\n'
            fout = open(fname, 'w')
            fout.write(''.join(contents))
            fout.close()
            p4.submit(fname, "bertha's edit to this")
        finally:
            os.chdir(top)

        # Andrew syncs and will have to resolve the changed file.
        try:
            os.chdir(andrew['home'])
            p4.sync(fname)
            result = p4.resolve(fname)
            self.failUnless(result[0]['action'].find('merge from') == 0)
            self.failUnless(result[0]['diff chunks']['yours'] == 1)
            self.failUnless(result[0]['diff chunks']['theirs'] == 1)
            self.failUnless(result[0]['diff chunks']['both'] == 0)
            self.failUnless(result[0]['diff chunks']['conflicting'] == 0)
            self.failUnless('depotFile' in result[0])
            self.failUnless('localFile' in result[0])
            self.failUnless('clientFile' in result[0])
            contents = open(fname, 'r').read()
            self.failUnless(contents.find('(bertha was here)') != -1)
            p4.revert(fname)    # cleanup
        finally:
            os.chdir(top)

    def test_resolve_ignored(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_resolve_ignored.txt'

        # Andrew creates a file and submits it. Edits it a submits it.
        # Then tries the 'p4 resolve -ay' it to the former revision.
        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            result = p4.submit(fname, 'first checkin of this file')
            earlyRev = result['files'][0]['rev']

            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write('line 10\n')
            fout.close()
            p4.submit(fname, 'add a line')

            p4.sync('%s#%d' % (fname, earlyRev))
            p4.edit(fname)
            p4.sync(fname)
            result = p4.resolve(fname, autoMode='y')
            self.failUnless(result[0]['action'].startswith('ignored'))
            self.failUnless('diff chunks' not in result[0])
            self.failUnless('depotFile' in result[0])
            self.failUnless('localFile' in result[0])
            self.failUnless('clientFile' in result[0])

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(ResolveTestCase)

