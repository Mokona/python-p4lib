import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options


FILELOG_OUTPUT = """//depot/file.py
... #4 change 1000 edit on 2014/11/21 by mokona@local (text) 'Edit the file.py'
... #3 change 999 edit on 2014/11/20 by mokona@local (text) 'Edit'
... #2 change 800 edit on 2014/10/20 by mokona@local (text) 'Edit'
... #1 change 700 add on 2014/10/10 by mtrent@other (text) 'Added the file'
"""

FILELOG_LONG_OUTPUT = """//depot/file.py
... #1 change 700 add on 2014/10/10 by mtrent@other (text)
\tAdded the file
\tBecause it's fun

//depot/other.py
... #1 change 700 add on 2014/10/10 by mtrent@other (text)
\tThis is a new file
... ... With some notes
"""


class FilelogTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_for_a_file(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        p4.filelog("//depot/...")
        p4lib._run.assert_called_with(['p4', 'filelog', '//depot/...'])

    def test_for_a_file_list(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        p4.filelog(["//depot/...", "//depot/sub/..."])
        p4lib._run.assert_called_with(['p4', 'filelog',
                                       '//depot/...', '//depot/sub/...'])

    def test_can_follow_integrations(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        p4.filelog("//depot/...", followIntegrations=True)
        p4lib._run.assert_called_with(['p4', 'filelog', '-i', '//depot/...'])

    def test_can_specify_max_revision(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        p4.filelog("//depot/...", maxRevs=4)
        p4lib._run.assert_called_with(['p4', 'filelog', '-m', '4', '//depot/...'])

    def test_must_specify_max_revision_as_int(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        self.assertRaises(p4lib.P4LibError, p4.filelog, "//depot/...",
                          maxRevs="4")

    def test_fills_output(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()

        result = p4.filelog("//depot/...")

        self.assertEqual(1, len(result))

        file_1 = result[0]
        self.assertEqual("//depot/file.py", file_1["depotFile"])

        revisions = file_1["revs"]
        self.assertEqual(4, len(revisions))

        rev_4 = revisions[0]
        self.assertEqual("edit", rev_4["action"])
        self.assertEqual(1000, rev_4["change"])
        self.assertEqual("local", rev_4["client"])
        self.assertEqual("2014/11/21", rev_4["date"])
        self.assertEqual("text", rev_4["type"])
        self.assertEqual([], rev_4["notes"])
        self.assertEqual(4, rev_4["rev"])
        self.assertEqual("mokona", rev_4["user"])
        self.assertEqual("Edit the file.py", rev_4["description"])

        rev_1 = revisions[3]
        self.assertEqual("add", rev_1["action"])
        self.assertEqual(700, rev_1["change"])
        self.assertEqual("other", rev_1["client"])
        self.assertEqual("2014/10/10", rev_1["date"])
        self.assertEqual("text", rev_1["type"])
        self.assertEqual([], rev_1["notes"])
        self.assertEqual(1, rev_1["rev"])
        self.assertEqual("mtrent", rev_1["user"])
        self.assertEqual("Added the file", rev_1["description"])

    def test_fills_long_output(self):
        change_stdout(FILELOG_LONG_OUTPUT)

        p4 = p4lib.P4()

        result = p4.filelog("//depot/...", longOutput=True)
        p4lib._run.assert_called_with(['p4', 'filelog', '-l', '//depot/...'])

        self.assertEqual(2, len(result))

        file_1 = result[0]
        self.assertEqual("//depot/file.py", file_1["depotFile"])

        revisions = file_1["revs"]
        self.assertEqual(1, len(revisions))

        rev_1 = revisions[0]
        self.assertEqual("add", rev_1["action"])
        self.assertEqual(700, rev_1["change"])
        self.assertEqual("other", rev_1["client"])
        self.assertEqual("2014/10/10", rev_1["date"])
        self.assertEqual("text", rev_1["type"])
        self.assertEqual(1, rev_1["rev"])
        self.assertEqual("mtrent", rev_1["user"])
        self.assertEqual([], rev_1["notes"])

        file_2 = result[1]
        self.assertEqual("//depot/other.py", file_2["depotFile"])

        revisions = file_2["revs"]
        rev_1 = revisions[0]
        
        self.assertEqual("This is a new file\n", rev_1["description"])
        self.assertEqual(['With some notes'], rev_1["notes"])

    def test_raw_result(self):
        change_stdout(FILELOG_OUTPUT)

        p4 = p4lib.P4()
        raw_result = p4.filelog(files="//depot/...", _raw=True)

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(FILELOG_OUTPUT, raw_result['stdout'])

    def test_with_options(self):
        test_options(self, "filelog", files="//depot/...",
                     expected=["filelog", "//depot/..."])
