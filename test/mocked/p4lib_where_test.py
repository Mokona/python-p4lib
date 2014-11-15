import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_raw_option


WHERE_OUTPUT = r"""-//depot/foo/Py-2_1/... //trentm-ra/foo/Py-2_1/... c:\trentm\foo\Py-2_1\...
//depot/foo/win/... //trentm-ra/foo/win/... c:\trentm\foo\win\...
//depot/foo/Py Exts.dsw //trentm-ra/foo/Py Exts.dsw c:\trentm\foo\Py Exts.dsw
//depot/foo/%1 //trentm-ra/foo/%1 c:\trentm\foo\%1"""


class WhereTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_global(self):
        change_stdout(WHERE_OUTPUT)

        p4 = p4lib.P4()
        result_files = p4.where()

        p4lib._run.assert_called_with(['p4', 'where'])
        self.assertEqual(4, len(result_files))

        file_0 = result_files[0]
        self.assertTrue(file_0["minus"])
        self.assertEqual(r"//depot/foo/Py-2_1/...", file_0["depotFile"])

        # As where cannot parse platform independant yet, skipped these asserts
        # self.assertEqual(r"//trentm-ra/foo/Py-2_1/...", file_0["clientFile"])
        # self.assertEqual(r"c:\trentm\foo\Py-2_1\...", file_0["localFile"])

    def test_with_file(self):
        p4 = p4lib.P4()
        p4.where(files="file.cpp")

        p4lib._run.assert_called_with(['p4', 'where', 'file.cpp'])

    def test_with_file_list(self):
        p4 = p4lib.P4()
        p4.where(files=["file.cpp", "other.cpp"])

        p4lib._run.assert_called_with(['p4', 'where', 'file.cpp', 'other.cpp'])

    def test_raw_result(self):
        change_stdout(WHERE_OUTPUT)

        p4 = p4lib.P4()
        raw_result = p4.where(files="file.cpp",
                              _raw=True)

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(WHERE_OUTPUT, raw_result['stdout'])

    def test_with_options(self):
        test_raw_option(self, "where", files='file.cpp',
                        expected=["where", "file.cpp"])
