import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


DIFF_OUTPUT = """==== //depot/file.py#12 - /home/mokona/file.py ====
diffline_1
diffline_2
"""


class DiffTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_of_a_file(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff("//depot/test.py")
        p4lib._run.assert_called_with(['p4', 'diff', '//depot/test.py'])

    def test_of_a_file_list(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff(["//depot/test.py", "//depot/test2.py"])
        p4lib._run.assert_called_with(['p4', 'diff',
                                       '//depot/test.py',
                                       '//depot/test2.py'])

    def test_can_specify_a_diff_format(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff("//depot/test.py", diffFormat="n")
        p4lib._run.assert_called_with(['p4', 'diff', '-dn',
                                       '//depot/test.py'])

        p4.diff("//depot/test.py", diffFormat="c")
        p4lib._run.assert_called_with(['p4', 'diff', '-dc',
                                       '//depot/test.py'])

        self.assertRaises(p4lib.P4LibError, p4.diff,
                          "//depot/test.py", diffFormat="z")

    def test_can_specify_force_flag(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff("//depot/test.py", force=True)
        p4lib._run.assert_called_with(['p4', 'diff', '-f',
                                       '//depot/test.py'])

    def test_can_specify_text_flag(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff("//depot/test.py", text=True)
        p4lib._run.assert_called_with(['p4', 'diff', '-t',
                                       '//depot/test.py'])

    def test_can_specify_satisfying_flag(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        p4.diff("//depot/test.py", satisfying="a")
        p4lib._run.assert_called_with(['p4', 'diff', '-sa',
                                       '//depot/test.py'])

        p4.diff("//depot/test.py", satisfying="d")
        p4lib._run.assert_called_with(['p4', 'diff', '-sd',
                                       '//depot/test.py'])

        self.assertRaises(p4lib.P4LibError, p4.diff,
                          "//depot/test.py", satisfying="z")

    def test_fills_output_with_diffs(self):
        change_stdout(DIFF_OUTPUT)

        p4 = p4lib.P4()

        result = p4.diff("//depot/test.py")

        self.assertEqual(1, len(result))
        
        expected = {'binary': False,
                    'rev': 12,
                    'depotFile': '//depot/file.py',
                    'localFile': '/home/mokona/file.py',
                    'text': 'diffline_1\ndiffline_2\n'}

        self.assertEqual(expected, result[0])

    def test_raw_result(self):
        test_raw_result(self, DIFF_OUTPUT, "diff", files="//depot/file.py")

    def test_with_options(self):
        test_options(self, "diff", files="//depot/file.py",
                     expected=["diff", "//depot/file.py"])
