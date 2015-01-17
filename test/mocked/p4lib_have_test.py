import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


HAVE_OUTPUT = "depot-file#4 - client-file"


class HaveTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_global(self):
        change_stdout(HAVE_OUTPUT)

        p4 = p4lib.P4()
        result_files = p4.have()

        p4lib._run.assert_called_with(['p4', 'have'])
        self.assertEqual(1, len(result_files))

        file_0 = result_files[0]
        self.assertEqual(r"depot-file", file_0["depotFile"])
        self.assertEqual(r"client-file", file_0["localFile"])
        self.assertEqual(4, file_0["rev"])

    def test_file(self):
        change_stdout(HAVE_OUTPUT)

        p4 = p4lib.P4()
        p4.have("file.cpp")

        p4lib._run.assert_called_with(['p4', 'have', 'file.cpp'])

    def test_file_list(self):
        change_stdout(HAVE_OUTPUT)

        p4 = p4lib.P4()
        p4.have(["file.cpp", "file2.cpp"])

        p4lib._run.assert_called_with(['p4', 'have', 'file.cpp', 'file2.cpp'])

    def test_raw_result(self):
        test_raw_result(self, HAVE_OUTPUT, "have", files="file.cpp")

    def test_with_options(self):
        test_options(self, "have", files="file.cpp",
                     expected=["have", "file.cpp"])
