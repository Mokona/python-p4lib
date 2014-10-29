#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 sync'."""

import os
import sys
import unittest
import pprint

import testsupport
from p4lib import P4, P4LibError


class SyncTestCase(unittest.TestCase):
    def test_sync_added_file(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        bertha = testsupport.users['bertha']
        p4 = P4()
        fname = 'test_sync_added_file.txt'

        try:
            os.chdir(andrew['home'])

            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'first checkin of this file')
        finally:
            os.chdir(top)

        try:
            os.chdir(bertha['home'])

            results = p4.sync(fname)
            self.failUnless(len(results) == 1)
            result = results[0]
            self.failUnless(result['comment'].startswith("added"))
            self.failUnless(result['depotFile'].endswith(fname))
            self.failUnless(result.has_key('rev'))
            self.failUnless(result.has_key('notes'))
        finally:
            os.chdir(top)

    def test_sync_added_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        bertha = testsupport.users['bertha']
        p4 = P4()
        fnames = ['test_sync_added_files_1.txt',
                  'test_sync_added_files_2.txt']

        try:
            os.chdir(andrew['home'])

            for fname in fnames:
                fout = open(fname, 'w')
                fout.write('Hello there.\n')
                fout.close()
            p4.add(fnames)
            p4.submit(fnames, 'for test_sync_added_files')
        finally:
            os.chdir(top)

        try:
            os.chdir(bertha['home'])

            results = p4.sync(fnames)
            self.failUnless(len(results) == len(fnames))
        finally:
            os.chdir(top)

    def test_sync_file_needing_resolve(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        bertha = testsupport.users['bertha']
        p4 = P4()
        fname = 'test_sync_file_needing_resolve.txt'

        try:
            os.chdir(andrew['home'])

            # Create the file.
            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'first checkin of this file')

            # Edit the file.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write('Hello again.\n')
            fout.close()
            p4.submit(fname, 'edit by andrew')
        finally:
            os.chdir(top)

        try:
            os.chdir(bertha['home'])

            # Sync to rev 1 and start edit the file.
            p4.sync(fname+"#1")
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write('Hi, from bertha.\n')
            fout.close()

            results = p4.sync(fname)
            self.failUnless(len(results) == 1)
            result = results[0]
            self.failUnless(result['comment'] ==\
                            "is opened and not being changed")
            self.failUnless(result['notes'][0].startswith("must resolve"))

            # Cleanup.
            p4.revert(fname)
        finally:
            os.chdir(top)



def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(SyncTestCase)

