import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


FLUSH_OUTPUT = """//depot/foo#1 - updating C:\\foo
//depot/foo#1 - is opened and not being changed
//depot/foo#1 - is opened at a later revision - not changed
//depot/foo#1 - deleted as C:\\foo
... //depot/foo - must resolve #2 before submitting
"""


class FlushTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(FLUSH_OUTPUT)
        self.p4 = p4lib.P4()

    def test_all(self):
        self.p4.flush()
        p4lib._run.assert_called_with(['p4', 'flush'])

    def test_a_file(self):
        self.p4.flush(files="/depot/test.cpp")
        p4lib._run.assert_called_with(['p4', 'flush', '/depot/test.cpp'])

    def test_a_file_list(self):
        FILELIST = ["/depot/test.cpp", "/depot/test2.cpp"]

        self.p4.flush(files=FILELIST)
        p4lib._run.assert_called_with(['p4', 'flush'] + FILELIST)

    def test_can_specify_force(self):
        self.p4.flush(force=True)
        p4lib._run.assert_called_with(['p4', 'flush', '-f'])

    def test_can_specify_dryrun(self):
        self.p4.flush(dryrun=True)
        p4lib._run.assert_called_with(['p4', 'flush', '-n'])

    def test_fills_result(self):
        result = self.p4.flush()

        expected = [{'comment': 'updating C:\\foo',
                     'notes': [],
                     'rev': 1,
                     'depotFile': '//depot/foo'},
                    {'comment': 'is opened and not being changed',
                     'notes': [],
                     'rev': 1,
                     'depotFile': '//depot/foo'},
                    {'comment': 'is opened at a later revision - not changed',
                     'notes': [],
                     'rev': 1,
                     'depotFile': '//depot/foo'},
                    {'comment': 'deleted as C:\\foo',
                     'notes': ['must resolve #2 before submitting'],
                     'rev': 1,
                     'depotFile': '//depot/foo'}]

        self.assertEqual(expected[0], result[0])
        self.assertEqual(expected[1], result[1])
        self.assertEqual(expected[2], result[2])
        self.assertEqual(expected[3], result[3])

    def test_raw_result(self):
        test_raw_result(self, FLUSH_OUTPUT, "flush")

    def test_with_options(self):
        test_options(self, "flush",
                     expected=["flush"])
