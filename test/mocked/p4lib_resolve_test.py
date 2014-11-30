import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


RESOLVE_OUTPUT = """/mnt/file/foo.txt - merging //depot/foo.txt#2
Diff chunks: 0 yours + 0 theirs + 0 both + 1 conflicting
//client-name/foo.txt - resolve skipped.
/mnt/file/foo.png - merging //depot/foo.png#3
Non-text diff: 0 yours + 1 theirs + 0 both + 0 conflicting
"""


class ResolveTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(RESOLVE_OUTPUT)
        self.p4 = p4lib.P4()

    def test_a_file(self):
        self.p4.resolve("//depot/test.py")
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a', '//depot/test.py'])

    def test_several_files(self):
        self.p4.resolve(["//depot/test.py", "//depot/test2.py"])
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a',
                                       '//depot/test.py',
                                       '//depot/test2.py'])

    def test_can_specify_force_flag(self):
        self.p4.resolve("//depot/test.py", force=True)
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a', '-f',
                                       '//depot/test.py'])

    def test_can_specify_dry_run(self):
        self.p4.resolve("//depot/test.py", dryrun=True)
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a', '-n',
                                       '//depot/test.py'])

    def test_can_specify_force_text(self):
        self.p4.resolve("//depot/test.py", text=True)
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a', '-t',
                                       '//depot/test.py'])

    def test_can_specify_verbose_flag(self):
        self.p4.resolve("//depot/test.py", verbose=True)
        p4lib._run.assert_called_with(['p4', 'resolve',
                                       '-a', '-v',
                                       '//depot/test.py'])

    def test_can_specify_auto_mode(self):
        def test_flag(p4, autoMode):
            p4.resolve("//depot/test.py", autoMode=autoMode)
            p4lib._run.assert_called_with(['p4', 'resolve',
                                           '-a' + autoMode,
                                           '//depot/test.py'])

        for flag in "fmsty":
            test_flag(self.p4, flag)

    def test_cannot_avoid_auto_mode(self):
        self.assertRaises(p4lib.P4LibError,
                          self.p4.resolve,
                          "//depot/test.py", autoMode=None)

    def test_fills_result(self):
        result = self.p4.resolve("//depot/test.py")

        self.assertEqual(2, len(result))

        expected_1 = {'clientFile': '//client-name/foo.txt',
                      'action': 'resolve skipped',
                      'diff chunks': {'theirs': 0,
                                      'both': 0, 'yours': 0, 'conflicting': 1},
                      'rev': 2,
                      'depotFile': '//depot/foo.txt',
                      'localFile': '/mnt/file/foo.txt'}
        self.assertEqual(expected_1, result[0])

        expected_2 = {'diff chunks': {'theirs': 1,
                                      'both': 0, 'yours': 0, 'conflicting': 0},
                      'rev': 3, 'depotFile': '//depot/foo.png',
                      'localFile': '/mnt/file/foo.png'}
        self.assertEqual(expected_2, result[1])

    def test_raw_result(self):
        test_raw_result(self, RESOLVE_OUTPUT, "resolve",
                        files="//depot/file.py")

    def test_with_options(self):
        test_options(self, "resolve", files="//depot/file.py",
                     expected=["resolve", "-a", "//depot/file.py"])

