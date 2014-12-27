#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 change'."""

import os
import unittest

import testsupport
from p4lib import P4, P4LibError


class ChangeTestCase(unittest.TestCase):
    def test_create_change(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname1 = 'test_create_change_1.txt'
            fname2 = 'test_create_change_2.txt'
            open(fname1, 'w').write('Hello there 1.\n')
            open(fname2, 'w').write('Hello there 2.\n')
            p4.add([fname1, fname2])
            result = p4.change([fname1, fname2], "my new change")
            self.failUnless('change' in result)
            cnum = result['change']
            self.failUnless(result['action'] == 'created')
            self.failUnless(result['comment'].find('2') != -1,
                            "Expected change to be created with 2 files. "\
                            "It was not. comment='%s'" % result['comment'])
            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert([fname1, fname2])
        finally:
            os.chdir(top)

    def test_create_change_with_unopened_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_create_change_with_unopened_files.txt'
            open(fname, 'w').write('Hello there.\n')
            self.failUnlessRaises(P4LibError, p4.change, fname,
                                  "my new change")
            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_create_change_without_desc(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_create_change_without_desc.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            # Without a desc the arguments are incomplete, therefore
            # expect an error.
            self.failUnlessRaises(P4LibError, p4.change, fname)
            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_create_change_implicit_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname1 = 'test_create_change_implicit_files_1.txt'
            fname2 = 'test_create_change_implicit_files_2.txt'
            open(fname1, 'w').write('Hello there 1.\n')
            open(fname2, 'w').write('Hello there 2.\n')
            p4.add([fname1, fname2])
            result = p4.change(description="with all currently open files")
            self.failUnless('change' in result)
            cnum = result['change']
            self.failUnless(result['action'] == 'created')
            self.failUnless(result['comment'].find('2') != -1,
                            "Expected change to be created with 2 files. "\
                            "It was not. comment='%s'" % result['comment'])
            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert([fname1, fname2])
        finally:
            os.chdir(top)

    def test_create_change_with_files_from_another_change(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_create_change_with_files_from_another_change.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            p4.change(fname, "put this in one change")
            self.failUnlessRaises(P4LibError, p4.change, fname,
                                  "try to add it to a new change")
            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_update_pending_change_desc(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_update_pending_change_desc.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            cnum = p4.change(fname, "create it")['change']
            before = p4.change(change=cnum)
            self.failUnless(before['description'] == "create it",
                            "Initial change description is not as created.")

            result = p4.change(description="change the desc", change=cnum)
            self.failUnless(result['change'] == cnum)
            self.failUnless(result['action'] == 'updated')

            after = p4.change(change=cnum)
            self.failUnless(after['description'] == "change the desc",
                            "Description was not actually changed!")
            self.failUnless(result['change'] == cnum,
                            "Change number returned after changing a spec "\
                            "was not the original change number.")

            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_update_pending_change_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname1 = 'test_update_pending_change_files_1.txt'
            open(fname1, 'w').write('Hello there 1.\n')
            fname2 = 'test_update_pending_change_files_2.txt'
            open(fname2, 'w').write('Hello there 2.\n')
            p4.add([fname1, fname2])
            cnum = p4.change([fname1, fname2], "create it")['change']

            # Remove one file.
            result = p4.change(files=[fname1], change=cnum)
            self.failUnless(result['change'] == cnum)
            self.failUnless(result['action'] == 'updated')
            self.failUnless('comment' in result)
            c = p4.change(change=cnum)
            self.failUnless(len(c['files']) == 1,
                            "Number of files was not changed.")

            # Remove all files.
            result = p4.change(files=[], change=cnum)
            self.failUnless(result['change'] == cnum)
            self.failUnless(result['action'] == 'updated')
            self.failUnless('comment' in result)
            c = p4.change(change=cnum)
            self.failIf('files' in c, "Number of files was not changed.")

            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert([fname1, fname2])
        finally:
            os.chdir(top)

    def test_update_pending_change_no_change(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_update_pending_change_no_change.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            cnum = p4.change(fname, "create it")['change']
            c = p4.change(description="create it", change=cnum)
            self.failUnless(c['change'] == cnum)
            #XXX Cannot satisfactorily test result of no change, because
            #    p4lib's built change form causes P4 to *think* that
            #    there was a change even though there was none.
            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_delete_pending_change_with_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_delete_pending_change_with_files.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            cnum = p4.change(fname, "create it")['change']
            result = p4.change(change=cnum, delete=1)
            self.failUnless(result['change'] == cnum)
            self.failIf('action' in result,
                "Deleting change should NOT have succeeded, but it did.")
            self.failUnless('comment' in result)
            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_delete_pending_change_no_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_delete_pending_change_no_files.txt'
            cnum = p4.change([], "create it")['change']
            result = p4.change(change=cnum, delete=1)
            self.failUnless(result['change'] == cnum)
            self.failUnless(result['action'] == 'deleted')
        finally:
            os.chdir(top)

    def test_get_pending_change_desc(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        try:
            os.chdir(andrew['home'])
            p4 = P4()
            fname = 'test_get_pending_change_desc.txt'
            open(fname, 'w').write('Hello there.\n')
            p4.add(fname)
            cnum = p4.change(fname, "my change")['change']
            c = p4.change(change=cnum)
            self.failUnless(c['user'] == 'andrew')
            self.failUnless(c['change'] == cnum)
            self.failUnless(c['description'] == "my change")
            self.failUnless(c['status'] == 'pending')
            self.failUnless(len(c['files']) == 1)
            self.failUnless(c['files'][0]['action'] == 'add')
            self.failUnless(c['files'][0]['depotFile'] ==\
                            p4.where(fname)[0]['depotFile'])
            # cleanup
            p4.change(files=[], change=cnum)
            p4.change(change=cnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    #XXX Implement when have p4.submit(...) implemented.
    #def test_get_submitted_change_desc(self):...


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(ChangeTestCase)

