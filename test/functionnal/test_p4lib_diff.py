#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 diff'."""

import os
import unittest
import stat

import testsupport
from p4lib import P4, P4LibError


class DiffTestCase(unittest.TestCase):
    def test_diff_formats(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_formats.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_formats')

            # Open it and make an edit to be able to diff.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()

            results = p4.diff(fname)
            result = results[0]
            self.failUnless(os.path.basename(result['depotFile']) == fname)
            self.failUnless(os.path.basename(result['localFile']) == fname)
            self.failUnless('rev' in result)
            self.failUnless(result['text'].find('> another line') != -1)

            result = p4.diff(fname, diffFormat='')[0]
            self.failUnless(result['text'].find('> another line') != -1)

            result = p4.diff(fname, diffFormat='n')[0]
            self.failUnless(result['text'].find('a10 1') != -1)
            self.failUnless(result['text'].find('another line') != -1)

            result = p4.diff(fname, diffFormat='c')[0]
            self.failUnless(result['text'].find('*' * 15) != -1)
            self.failUnless(result['text'].find('+ another line') != -1)

            result = p4.diff(fname, diffFormat='s')[0]
            self.failUnless(result['text'].find('add 1 chunks 1 lines') != -1)

            result = p4.diff(fname, diffFormat='u')[0]
            self.failUnless(result['text'].find('+another line') != -1)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_no_changes(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_no_changes.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_no_changes')

            # Open it and make NO edits.
            p4.edit(fname)

            results = p4.diff(fname)
            result = results[0]
            self.failUnless(os.path.basename(result['depotFile']) == fname)
            self.failUnless(os.path.basename(result['localFile']) == fname)
            self.failUnless('rev' in result)
            self.failIf('text' in result)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_satisfying_a(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_satisfying_a.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_satisfying_a')

            # Open it and make NO edits.
            p4.edit(fname)
            results = p4.diff(fname, satisfying='a')
            self.failIf(results)

            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            result = p4.diff(fname, satisfying='a')[0]
            self.failUnless(os.path.basename(result['localFile']) == fname)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_satisfying_d(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_satisfying_d.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_satisfying_d')

            results = p4.diff(fname, satisfying='d')
            self.failIf(results)

            os.chmod(fname, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            os.remove(fname)
            result = p4.diff(fname, satisfying='d')[0]
            self.failUnless(os.path.basename(result['localFile']) == fname)
        finally:
            os.chdir(top)

    def test_diff_satisfying_e(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_satisfying_e.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_satisfying_e')

            results = p4.diff(fname, satisfying='e')
            self.failIf(results)

            # Make an edit but do NOT open it for edit.
            os.chmod(fname, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            result = p4.diff(fname, satisfying='e')[0]
            self.failUnless(os.path.basename(result['localFile']) == fname)
        finally:
            os.chdir(top)

    def test_diff_satisfying_r(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_satisfying_r.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_satisfying_r')

            results = p4.diff(fname, satisfying='r')
            self.failIf(results)

            # Open it and make NO edits.
            p4.edit(fname)
            result = p4.diff(fname, satisfying='r')[0]
            self.failUnless(os.path.basename(result['localFile']) == fname)

            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            results = p4.diff(fname, satisfying='r')
            self.failIf(results)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_force(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_force.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_force')

            # Make an edit but do NOT open it for edit.
            os.chmod(fname, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()

            results = p4.diff(fname)
            self.failIf(results)

            results = p4.diff(fname, force=1)
            result = results[0]
            self.failUnless(os.path.basename(result['depotFile']) == fname)
            self.failUnless(os.path.basename(result['localFile']) == fname)
            self.failUnless('rev' in result)
            self.failUnless(result['text'].find('> another line') != -1)
        finally:
            os.chdir(top)

    def test_diff_binary(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file (make it binary).
            fname = 'test_diff_binary.txt'
            fout = open(fname, 'w')
            for i in range(10):
                fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname, filetype='binary')
            p4.submit(fname, 'for test_diff_binary')

            # Open for edit and make a change.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()

            result = p4.diff(fname)[0]
            self.failUnless(os.path.basename(result['depotFile']) == fname)
            self.failUnless(os.path.basename(result['localFile']) == fname)
            self.failUnless('rev' in result)
            self.failUnless(isinstance(result['notes'], list))
            self.failIf('text' in result)

            result = p4.diff(fname, text=1)[0]
            self.failUnless(os.path.basename(result['depotFile']) == fname)
            self.failUnless(os.path.basename(result['localFile']) == fname)
            self.failUnless('rev' in result)
            self.failUnless(result['text'].find('> another line') != -1)
            self.failIf('notes' in result)

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_bogus_args(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname = 'test_diff_bogus_args.txt'
            fout = open(fname, 'w')
            for i in range(10): fout.write("line %d\n" % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, 'for test_diff_bogus_args')

            # Open for edit and make a change.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()

            self.failUnlessRaises(P4LibError, p4.diff, fname, diffFormat='q')
            self.failUnlessRaises(P4LibError, p4.diff, fname, satisfying='q')

            # cleanup
            p4.revert(fname)
        finally:
            os.chdir(top)

    def test_diff_multiple_files(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()
        try:
            os.chdir(andrew['home'])
            # Submit a first revision of a test file.
            fname1 = 'test_diff_multiple_files_1.txt'
            fname2 = 'test_diff_multiple_files_2.txt'
            fnames = [fname1, fname2]
            for fname in fnames:
                fout = open(fname, 'w')
                for i in range(10):
                    fout.write("line %d\n" % i)
                fout.close()
            p4.add([fname1, fname2])
            p4.submit([fname1, fname2], 'for test_diff_multiple_files')

            # Open for edit and make a change.
            p4.edit(fnames)
            for fname in fnames:
                fout = open(fname, 'a')
                fout.write("another line\n")
                fout.close()

            results = p4.diff(fnames)
            self.failUnless(len(results) == 2)
            for result in results:
                self.failUnless(os.path.basename(result['depotFile']) in fnames)
                self.failUnless(os.path.basename(result['localFile']) in fnames)
                self.failUnless('rev' in result)
                self.failUnless(result['text'].find('> another line') != -1)

            # cleanup
            p4.revert(fnames)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(DiffTestCase)
