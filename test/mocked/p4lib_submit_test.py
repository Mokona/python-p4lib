import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


SUBMIT_OUTPUT = """Change 1 created with 2 open file(s).
Submitting change 1.
Locking 2 files ...
add //depot/test_simple_submit.txt#1
edit //depot/test_other_submit.txt#3
Change 1 submitted.
//depot/test_simple_submit.txt#1 - refreshing
//depot/test_other_submit.txt#3 - refreshing
"""

TEMPORARY_FILENAME = "tempFile"
DESCRIPTION = "a changelist description"


class SubmitTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')

        change_stdout(SUBMIT_OUTPUT)
        self.p4 = p4lib.P4()

    def test_a_file(self):
        self.p4.where = Mock(spec='p4lib.where')
        self.p4.where.return_value = []

        self.p4.submit("/depot/test.txt", DESCRIPTION)

        p4lib._run.assert_called_with(['p4', 'submit',
                                       '-i', '<', 'tempFile'])

        self.p4.where.assert_called_with(['/depot/test.txt'])

    def test_a_file_list(self):
        FILELIST = ["/depot/test.txt", "/depot/test2.txt"]

        self.p4.where = Mock(spec='p4lib.where')
        self.p4.where.return_value = []

        self.p4.submit(FILELIST, DESCRIPTION)

        p4lib._run.assert_called_with(['p4', 'submit',
                                       '-i', '<', 'tempFile'])

        self.p4.where.assert_called_with(FILELIST)

    def test_default_file_list(self):
        self.p4.opened = Mock(spec='p4lib.opened')
        self.p4.opened.return_value = []

        self.p4.submit(files=[], description=DESCRIPTION)

        self.assertTrue(self.p4.opened.called)

    def test_a_changelist(self):
        self.p4.submit(change=1234)

        p4lib._run.assert_called_with(['p4', 'submit',
                                       '-c', '1234'])

    def test_has_forbidden_parameter_combinations(self):
        self.assertRaises(p4lib.P4LibError, self.p4.submit, change=1234,
                          description=DESCRIPTION)
        self.assertRaises(p4lib.P4LibError, self.p4.submit, files=None,
                          description=DESCRIPTION)

    def test_fills_results(self):
        result = self.p4.submit(change=1234)

        self.assertEqual("submitted", result["action"])
        self.assertEqual(1, result["change"])

        files = result["files"]
        self.assertEqual(2, len(files))

        expected_1 = {'action': 'add', 'rev': 1,
                      'depotFile': '//depot/test_simple_submit.txt'}
        expected_2 = {'action': 'edit', 'rev': 3,
                      'depotFile': '//depot/test_other_submit.txt'}

        self.assertEqual(expected_1, files[0])
        self.assertEqual(expected_2, files[1])

    def test_raw_result(self):
        test_raw_result(self, SUBMIT_OUTPUT, "submit", change=1234)

    def test_with_options(self):
        test_options(self, "submit", change=1234,
                     expected=["submit", "-c", '1234'])
