import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


FILES_OUTPUT = """//depot/file.txt#2 - edit change 1234 (text)
//depot/file2.txt#1 - add change 5678 (text)
//depot/file3.txt#1 - move/delete change 9854 (text)"""


class FilesTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_list_file(self):
        change_stdout(FILES_OUTPUT)

        p4 = p4lib.P4()

        result = p4.files("//depot/...")
        p4lib._run.assert_called_with(['p4', 'files', '//depot/...'])

        file_1 = result[0]

        self.assertIn("depotFile", file_1)
        self.assertIn("rev", file_1)
        self.assertIn("type", file_1)
        self.assertIn("change", file_1)
        self.assertIn("action", file_1)

        self.assertEqual("//depot/file.txt", file_1["depotFile"])
        self.assertEqual(2, file_1["rev"])
        self.assertEqual("text", file_1["type"])
        self.assertEqual(1234, file_1["change"])
        self.assertEqual("edit", file_1["action"])

        file_2 = result[1]

        self.assertEqual("//depot/file2.txt", file_2["depotFile"])
        self.assertEqual(1, file_2["rev"])
        self.assertEqual("text", file_2["type"])
        self.assertEqual(5678, file_2["change"])
        self.assertEqual("add", file_2["action"])

        file_3 = result[2]

        self.assertEqual("move/delete", file_3["action"])

    def test_accepts_revision_range(self):
        filename = "//depot/file.c@123,@now"

        change_stdout(FILES_OUTPUT)

        p4 = p4lib.P4()

        p4.files(filename)
        p4lib._run.assert_called_with(['p4', 'files', filename])

    def test_accepts_revision_range_and_arobas(self):
        filename = "//depot/file@.c@123,@now"
        expected = "//depot/file%40.c@123,@now"

        change_stdout(FILES_OUTPUT)

        p4 = p4lib.P4()

        p4.files(filename)
        p4lib._run.assert_called_with(['p4', 'files', expected])

    def test_raw_result(self):
        test_raw_result(self, FILES_OUTPUT, "files", files="//depot/...")

    def test_with_options(self):
        test_options(self, "files", files="//depot/...",
                     expected=["files", "//depot/..."])
