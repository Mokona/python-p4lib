import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


DELETE_OUTPUT = """//depot/test.txt#3 - opened for delete
//depot/foo.txt - can't delete (already opened for edit)
"""


class DeleteTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(DELETE_OUTPUT)
        self.p4 = p4lib.P4()

    def test_a_file(self):
        self.p4.delete(files="/depot/test.txt")

        p4lib._run.assert_called_with(['p4', 'delete',
                                       '/depot/test.txt'])

    def test_a_file_list(self):
        FILELIST = ["/depot/test.txt", "/depot/test2.txt"]

        self.p4.delete(files=FILELIST)

        p4lib._run.assert_called_with(['p4', 'delete'] + FILELIST)

    def test_can_specify_a_changelist(self):
        self.p4.delete(files="/depot/test.txt", change=1234)

        p4lib._run.assert_called_with(['p4', 'delete', '-c', '1234',
                                       '/depot/test.txt'])

    def test_fills_results(self):
        result = self.p4.delete(files="/depot/test.txt")

        self.assertEqual(2, len(result))

        expected_1 = {'comment': 'opened for delete',
                      'rev': 3,
                      'depotFile': '//depot/test.txt'}
        file_1 = result[0]

        self.assertEqual(expected_1, file_1)

        expected_2 = {'comment': "can't delete (already opened for edit)",
                      'rev': None,
                      'depotFile': '//depot/foo.txt'}
        file_2 = result[1]

        self.assertEqual(expected_2, file_2)

    def test_raw_result(self):
        test_raw_result(self, DELETE_OUTPUT, "delete", files="/depot/test.txt")

    def test_with_options(self):
        test_options(self, "delete", files="/depot/test.txt",
                     expected=["delete", "/depot/test.txt"])
