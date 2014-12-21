import unittest
import p4lib
from unittest.mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


REVERT_OUTPUT = """//depot/hello.txt#1 - was edit, reverted
//depot/test_g.txt#none - was add, abandoned
"""


class RevertTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_a_file(self):
        change_stdout(REVERT_OUTPUT)

        p4 = p4lib.P4()

        p4.revert("//depot/test.py")
        p4lib._run.assert_called_with(['p4', 'revert', '//depot/test.py'])

    def test_a_file_list(self):
        change_stdout(REVERT_OUTPUT)

        p4 = p4lib.P4()

        p4.revert(["//depot/test.py", "//depot/test2.py"])
        p4lib._run.assert_called_with(['p4', 'revert',
                                       '//depot/test.py',
                                       '//depot/test2.py'])

    def test_can_specify_a_change_list(self):
        change_stdout(REVERT_OUTPUT)

        p4 = p4lib.P4()

        p4.revert("//depot/test.py", change=1234)
        p4lib._run.assert_called_with(['p4', 'revert', '-c', '1234',
                                       '//depot/test.py'])

    def test_can_specify_unchanged_only(self):
        change_stdout(REVERT_OUTPUT)

        p4 = p4lib.P4()

        p4.revert("//depot/test.py", unchangedOnly=True)
        p4lib._run.assert_called_with(['p4', 'revert', '-a',
                                       '//depot/test.py'])

    def test_fills_output(self):
        change_stdout(REVERT_OUTPUT)

        p4 = p4lib.P4()

        result = p4.revert("//depot/test.py")
        p4lib._run.assert_called_with(['p4', 'revert', '//depot/test.py'])

        self.assertEqual(2, len(result))

        expected_1 = {'comment': 'was edit, reverted',
                      'rev': 1,
                      'depotFile': '//depot/hello.txt'}
        expected_2 = {'comment': 'was add, abandoned',
                      'rev': 'none',
                      'depotFile': '//depot/test_g.txt'}
        self.assertEqual(expected_1, result[0])
        self.assertEqual(expected_2, result[1])

    def test_raw_result(self):
        test_raw_result(self, REVERT_OUTPUT, "revert",
                        files="//depot/file.py")

    def test_with_options(self):
        test_options(self, "revert", files="//depot/file.py",
                     expected=["revert", "//depot/file.py"])

