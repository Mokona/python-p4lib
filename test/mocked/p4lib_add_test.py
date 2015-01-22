import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


ADD_OUTPUT_1 = r"//depot/file.cpp#1 - opened for add"
ADD_OUTPUT_2 = r"""//depot/apps/px.py - can't add (already opened for edit)
... //depot/apps/px.py - warning: add of existing file

//depot/test.cpp - can't add existing file
"""

ADD_FILENAME = "//depot/file.cpp"
ADD_FILENAMES = ["//depot/file.cpp", "//depot/apps/px.py"]


class AddTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_a_file(self):
        change_stdout(ADD_OUTPUT_1)

        p4 = p4lib.P4()

        result = p4.add(ADD_FILENAME)
        p4lib._run.assert_called_with(['p4', 'add', ADD_FILENAME])

        file_1 = result[0]

        self.assertIn("depotFile", file_1)
        self.assertIn("rev", file_1)
        self.assertIn("comment", file_1)

        self.assertEqual(ADD_FILENAME, file_1["depotFile"])
        self.assertEqual(1, file_1["rev"])
        self.assertEqual("opened for add", file_1["comment"])

    def test_some_files(self):
        change_stdout(ADD_OUTPUT_2)

        p4 = p4lib.P4()

        result = p4.add(ADD_FILENAMES)

        p4lib._run.assert_called_with(['p4', 'add'] + ADD_FILENAMES)

        self.assertEqual(2, len(result))

        file_1 = result[0]

        self.assertEqual("//depot/apps/px.py", file_1["depotFile"])
        self.assertEqual(None, file_1["rev"])
        self.assertEqual("can't add (already opened for edit)",
                         file_1["comment"])

        file_2 = result[1]

        self.assertEqual("//depot/test.cpp", file_2["depotFile"])
        self.assertEqual(None, file_2["rev"])
        self.assertEqual("can't add existing file", file_2["comment"])

    def test_can_specify_filetype(self):
        change_stdout(ADD_OUTPUT_1)

        p4 = p4lib.P4()

        p4.add(ADD_FILENAME, filetype='text')

        p4lib._run.assert_called_with(['p4', 'add',
                                       '-t', 'text', ADD_FILENAME])

    def test_with_special_char_causes_force(self):
        change_stdout(ADD_OUTPUT_1)

        p4 = p4lib.P4()

        FILENAME = "//depot/file_speci@l_char.txt"

        p4.add(FILENAME)
        p4lib._run.assert_called_with(['p4', 'add', '-f', FILENAME])

    def test_can_specify_change(self):
        change_stdout(ADD_OUTPUT_1)

        p4 = p4lib.P4()

        p4.add(ADD_FILENAME, change=1234)

        p4lib._run.assert_called_with(['p4', 'add',
                                       '-c', '1234', ADD_FILENAME])

    def test_raw_result(self):
        test_raw_result(self, ADD_OUTPUT_1, "add",
                        files=ADD_FILENAME)

    def test_with_options(self):
        test_options(self, "add", files=ADD_FILENAME,
                     expected=["add", ADD_FILENAME])
