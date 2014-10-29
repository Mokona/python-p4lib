#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test px.py's interface to 'p4 genpatch'."""

import os
import sys
import unittest
import pprint

import testsupport

from p4lib import P4, P4LibError


class GenpatchTestCase(unittest.TestCase):
    #TODO:
    #   - def test_genpatch_in_px_help_commands
    #   - def test_genpatch_in_px_help_px
    #   - def test_px_help_genpatch
    #   - need filespec limiting in 'px genpatch' first for these:
    #       def test_submitted_filespec_limited(self):
    #       def test_pending_filespec_limited(self):
    #       def test_pending_default_filespec_limited(self):
    #   - need p4lib.P4.branch before can easily test this
    #       def test_branched_file(self):
    #

    def _applyPatch(self, patch):
        """Apply the given patch data."""
        if 1:
            cmd = 'patch -p0'
            if sys.platform.startswith('win'):
                i, o, e = os.popen3(cmd)
                i.write(patch)
                i.close()
                e.close()
                o.close()
            else:
                import popen2
                p = popen2.Popen3(cmd, 1)
                i, o, e = p.tochild, p.fromchild, p.childerr
                i.write(patch)
                i.close()
                e.close()
                o.close()
                p.wait()
        else:
            # If you want to *see* the patch process use this block.
            # (Useful for debugging.)
            tmpfile = "patchfile.tmp"
            fout = open(tmpfile, 'w')
            fout.write(patch)
            fout.close()
            os.system('patch -p0 < %s' % tmpfile)

    def test_submitted(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_submitted.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "first submission")

            # Make a second revision.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            change = p4.submit(fname, "add another line")['change']

            # Generate a patch for the last change.
            argv = ['px', 'genpatch', str(change)]
            output, error, retval = testsupport.run(argv)
            self.failIf(error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.sync(fname+"#1")
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_pending(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_pending.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "first submission")

            # Make a pending change with edits.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()
            change = p4.change(fname, "my pending edits")['change']

            # Generate a patch for the default pending change.
            argv = ['px', 'genpatch', str(change)]
            output, error, retval = testsupport.run(argv)
            self.failIf(error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.revert(fname)
            p4.sync(fname+"#1")
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_no_change_in_one_of_the_files(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_pending_no_change_in_one_of_the_files.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "first submission")

            # Make a pending change with *no* change in at least one of
            # the files.
            p4.edit(fname)

            # Generate a patch for the default pending change.
            argv = ['px', 'genpatch', 'default']
            output, error, retval = testsupport.run(argv)
            self.failIf(error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.revert(fname)
            p4.sync(fname+"#1")
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_empty_added_file(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_empty_added_file.txt'

        try:
            os.chdir(andrew['home'])

            # "Add" a file that does not exist.
            p4.add(fname)

            # Generate a patch for the default pending change.
            argv = ['px', 'genpatch', 'default']
            output, error, retval = testsupport.run(argv)
            self.failIf(error, "This command, %r, failed with this error "\
                               "output: %s" % (argv, error))
            self.failIf(retval)
            patch = ''.join(output)
        finally:
            p4.revert(fname)
            os.chdir(top)

    def test_pending_default(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_pending_default.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "first submission")

            # Make a edits in the default changelist.
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line\n")
            fout.close()

            # Generate a patch for the default pending change.
            argv = ['px', 'genpatch']
            output, error, retval = testsupport.run(argv)
            self.failIf(error, "Unexpected error output: %r" % error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.revert(fname)
            p4.sync(fname+"#1")
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_added_file(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_added_file.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            change = p4.submit(fname, "first submission")['change']

            # Generate a patch for the last change.
            argv = ['px', 'genpatch', str(change)]
            output, error, retval = testsupport.run(argv)
            self.failIf(error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            os.chmod(fname, 0777)
            os.remove(fname)
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_added_file_pending(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_added_file_pending.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)

            # Generate a patch for the default pending changelist.
            argv = ['px', 'genpatch']
            output, error, retval = testsupport.run(argv)
            self.failIf(error, "Unexpected error output: %r" % error)
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.revert(fname)
            os.chmod(fname, 0777)
            os.remove(fname)
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")
        finally:
            os.chdir(top)

    def test_added_binary_file(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_added_binary_file.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname, filetype='binary')
            change = p4.submit(fname, "first submission")['change']

            # Generate a patch for the last change.
            argv = ['px', 'genpatch', str(change)]
            output, error, retval = testsupport.run(argv)
            self.failUnless(error[0].startswith('warn:'),
                            "Did not get expected warning for not being "\
                            "able to inline the adde dbinary file.")
            self.failIf(retval)
            patch = ''.join(output)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            os.chmod(fname, 0777)
            os.remove(fname)
            self._applyPatch(patch)
            self.failIf(os.path.exists(fname),
                        "Did not expect patch to re-create the binary "\
                        "file: %r" % fname)
        finally:
            os.chdir(top)

    def test_no_newline_at_end_of_file(self):
        p4 = P4()
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        fname = 'test_no_newline_at_end_of_file.txt'

        try:
            os.chdir(andrew['home'])
            # Make the first revision.
            fout = open(fname, 'w')
            for i in range(10): fout.write('line %d\n' % i)
            fout.close()
            p4.add(fname)
            p4.submit(fname, "first submission")

            # Make a second revision (with *no* trailing newline)
            p4.edit(fname)
            fout = open(fname, 'a')
            fout.write("another line")
            fout.close()
            change = p4.submit(fname, "add another line")['change']

            # Generate a patch for the last change.
            argv = ['px', 'genpatch', str(change)]
            output, error, retval = testsupport.run(argv)
            self.failIf(error)
            self.failIf(retval)
            patch = ''.join(output)
            self.failUnless(patch.find("No newline at end of file") != -1)

            # Sync back to before the change, apply the patch, and see
            # if the results are the same as the actual change.
            before = open(fname, 'r').read()
            p4.sync(fname+"#1")
            self._applyPatch(patch)
            after = open(fname, 'r').read()
            if after.endswith('\n'):
                # This is sort of cheating the test, but 'patch' ignores
                # the correctly placed '/ No newline at end of file'
                # that both "diff" and "px genpatch" produce. What are
                # you gonna do?
                after = after[:-1]
            self.failUnless(before == after,
                            "Applying the generated patch did not work.")

        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(GenpatchTestCase)

