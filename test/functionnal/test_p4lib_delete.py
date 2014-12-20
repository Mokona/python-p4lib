#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 delete'."""

import os
import unittest

import testsupport
from p4lib import P4, P4LibError


class DeleteTestCase(unittest.TestCase):
    def test_delete(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # First add and submit a file.
            fname = 'test_delete.txt'
            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'add this file to be deleted')

            # Now delete the file.
            result = p4.delete(fname)
            self.failUnless(result[0]['comment'] == 'opened for delete')

            self.failUnless(result[0]['depotFile']
                            == p4.where(fname)[0]['depotFile'])
            self.failUnless(isinstance(result[0]['rev'], int))
            opened = p4.opened(fname)
            self.failUnless(opened[0]['action'] == 'delete')
            self.failUnless(opened[0]['depotFile'] == result[0]['depotFile'])

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_delete_multiple_files(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # First add and submit some files.
            fname1 = 'test_delete_multiple_files_1.txt'
            fname2 = 'test_delete_multiple_files_2.txt'
            open(fname1, 'w').write('Hello there 1.\n')
            open(fname2, 'w').write('Hello there 2.\n')
            p4.add([fname1, fname2])
            p4.submit([fname1, fname2], 'add files to be deleted')

            # Now delete the files.
            results = p4.delete([fname1, fname2])
            for result in results:
                self.failUnless(result['comment'] == 'opened for delete')
                self.failUnless(isinstance(result['rev'], int))

            # cleanup
            p4.revert([fname1, fname2])
        finally:
            os.chdir(top)

    def test_delete_already_opened(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # First add and submit a file.
            fname = 'test_delete_already_opened.txt'
            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'add this file to be deleted')

            # Now open it and then try to delete it.
            p4.edit(fname)
            result = p4.delete(fname)
            self.failUnless(result[0]['comment'] != 'opened for delete')
            self.failUnless(result[0]['rev'] is None)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_delete_specify_change(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # First add and submit a file.
            fname = 'test_delete_specify_change.txt'
            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'add this file to be deleted')

            # Now delete the file (specifying an existing pending
            # change).
            c = p4.change([], 'empty pending change for deleted files')
            cnum = c['change']
            result = p4.delete(fname, change=cnum)
            self.failUnless(result[0]['depotFile']
                            == p4.where(fname)[0]['depotFile'])
            self.failUnless(isinstance(result[0]['rev'], int))
            c = p4.change(change=cnum)
            self.failUnless(c['files'][0]['depotFile']
                            == result[0]['depotFile'])
            self.failUnless(c['files'][0]['action'] == 'delete')

            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_delete_specify_bogus_change(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            # First add and submit a file.
            fname = 'test_delete_specify_bogus_change.txt'
            fout = open(fname, 'w')
            fout.write('Hello there.\n')
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'add this file to be deleted')

            latestCnum = p4.changes(maximum=1)[0]['change']
            # Specify an already submitted change.
            self.failUnlessRaises(P4LibError, p4.delete, fname,
                                  change=latestCnum)
            # Specify a non-existant change.
            self.failUnlessRaises(P4LibError, p4.delete, fname,
                                  change=latestCnum + 1)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(DeleteTestCase)

