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

import testsupport
from p4lib import P4, P4LibError


class BackoutTestCase(unittest.TestCase):
    #TODO:
    #   - test with more complex changes
    def test_backout_add(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_backout_add.txt'

        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            result = p4.submit(fname, 'first checkin of this file')
            self.failUnless(result['action'] == 'submitted')
            cnum = result['change']
            argv = ['px', 'backout', str(cnum)]
            output, error, retval = testsupport.run(argv)

            lineRe = re.compile('^Change (\d+) created to backout change '\
                                '(\d+)\.$')
            match = lineRe.match(output[0])
            self.failUnless(match, "Unknown 'px backout' first output "\
                                   "line: '%s'." % output[0])
            self.failUnless(int(match.group(2)) == cnum)
            pendingCnum = int(match.group(1))
            c = p4.change(change=pendingCnum)
            self.failUnless(c['description'].startswith("Backout change"))
            self.failUnless(len(c['files']) == 1)
            self.failUnless(c['files'][0]['action'] == 'delete')
            self.failUnless(c['files'][0]['depotFile']
                            == p4.where(fname)[0]['depotFile'])

            # cleanup
            p4.change([], change=pendingCnum)
            p4.change(change=pendingCnum, delete=1)
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_backout_addeditdelete(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fnameAdd = 'test_backout_addeditdelete_add.txt'
        fnameEdit = 'test_backout_addeditdelete_edit.txt'
        fnameDelete = 'test_backout_addeditdelete_delete.txt'

        try:
            os.chdir(andrew['home'])
            # Make this change:
            #   ... //depot/foo#1 add
            #   ... //depot/bar#3 delete
            #   ... //depot/ola#4 edit
            fout = open(fnameEdit, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            fout = open(fnameDelete, 'w')
            fout.write("Hello from the add file.")
            fout.close()
            p4.add([fnameEdit, fnameDelete])
            p4.submit([fnameEdit, fnameDelete],
                      'setup for test_backout_addeditdelete')

            p4.delete(fnameDelete)
            p4.edit(fnameEdit)
            contents = open(fnameEdit, 'r').readlines()
            contents[0] = contents[0][:-1] + " (hello again)\n"
            fout = open(fnameEdit, 'w')
            fout.write(''.join(contents))
            fout.close()
            fout = open(fnameAdd, 'w')
            fout.write("Hello from the add file.")
            fout.close()
            p4.add(fnameAdd)
            result = p4.submit([fnameAdd, fnameEdit, fnameDelete],
                               'test submission to backout')
            cnum = result['change']

            argv = ['px', 'backout', str(cnum)]
            output, error, retval = testsupport.run(argv)

            lineRe = re.compile('^Change (\d+) created to backout change '\
                                '(\d+)\.$')
            match = lineRe.match(output[0])
            self.failUnless(match, "Unknown 'px backout' first output "\
                                   "line: '%s'." % output[0])
            self.failUnless(int(match.group(2)) == cnum)
            pendingCnum = int(match.group(1))
            c = p4.change(change=pendingCnum)
            self.failUnless(c['description'].startswith("Backout change"))
            self.failUnless(len(c['files']) == 3)
            for file in c['files']:
                localFile = p4.where(file['depotFile'])[0]['localFile']
                basename = os.path.basename(localFile)
                if basename == fnameAdd:
                    self.failUnless(file['action'] == 'delete')
                if basename == fnameDelete:
                    self.failUnless(file['action'] == 'add')
                if basename == fnameEdit:
                    self.failUnless(file['action'] == 'edit')

            # cleanup
            p4.change([], change=pendingCnum)
            p4.change(change=pendingCnum, delete=1)
            p4.revert([fnameAdd, fnameDelete, fnameEdit])
        finally:
            os.chdir(top)

    def test_backout_with_space(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_backout_with space.txt'

        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            result = p4.submit(fname, 'first checkin of this file')
            self.failUnless(result['action'] == 'submitted')
            cnum = result['change']
            argv = ['px', 'backout', str(cnum)]
            output, error, retval = testsupport.run(argv)
            self.failUnless(retval, "This call should have failed but did "\
                                    "not: argv=%s" % argv)
        finally:
            os.chdir(top)

    def test_backout_files_already_open(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_backout_files_already_open.txt'

        try:
            os.chdir(andrew['home'])
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            result = p4.submit(fname, 'first checkin of this file')
            self.failUnless(result['action'] == 'submitted')
            cnum = result['change']

            p4.edit(fname)
            argv = ['px', 'backout', str(cnum)]
            output, error, retval = testsupport.run(argv)
            self.failUnless(retval, "This call should have failed but did "\
                                    "not: argv=%s" % argv)

            # Cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(BackoutTestCase)

