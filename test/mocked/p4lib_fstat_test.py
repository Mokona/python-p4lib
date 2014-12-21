import unittest
import p4lib
from unittest.mock import Mock
from test_utils import change_stdout
from test_utils import test_options, test_raw_result


FSTAT_OUTPUT = """... clientFile /client/file1.cpp
... depotFile /depot/file1.cpp
... path /path/to/file1.cpp
... headAction edit
... headChange 2
... headRev 2
... headType text
... headTime 1234
... haveRev 1
... action edit
... actionOwner edit
... change 123
... unresolved true
... ourLock true

... clientFile /client/file2.cpp
... depotFile /depot/file2.cpp
... path /path/to/file1.cpp
... headAction add
... headChange 1
... headRev 1
... headType text
... headTime 4321

"""


class FStatTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        self.p4 = p4lib.P4()
        change_stdout(FSTAT_OUTPUT)

    def test_on_a_file(self):
        self.p4.fstat("/depot/test.cpp")
        
        p4lib._run.assert_called_with(['p4', 'fstat', '-C', '-P',
                                       '/depot/test.cpp'])
    
    def test_on_a_file_list(self):
        FILELIST = ["/depot/test.txt", "/depot/test2.txt"]
        self.p4.fstat(FILELIST)
        
        p4lib._run.assert_called_with(['p4', 'fstat', '-C', '-P'] +
                                      FILELIST)

    def test_must_give_files(self):
        self.assertRaises(p4lib.P4LibError, self.p4.fstat, [])

    def test_fills_results(self):
        result = self.p4.fstat("/depot/test.cpp")

        self.assertEqual(2, len(result))

        expected1 = {'unresolved': 'true',
                     'ourLock': 1,
                     'haveRev': 1,
                     'headAction': 'edit',
                     'headType': 'text',
                     'clientFile': '/client/file1.cpp',
                     'change': '123',
                     'action': 'edit',
                     'actionOwner': 'edit',
                     'headTime': 1234,
                     'headChange': 2,
                     'depotFile': '/depot/file1.cpp',
                     'path': '/path/to/file1.cpp',
                     'headRev': 2}

        self.assertEqual(expected1, result[0])

        expected2 = {'unresolved': '',
                     'ourLock': 0,
                     'haveRev': 0,
                     'headAction': 'add',
                     'actionOwner': '',
                     'headType': 'text',
                     'clientFile': '/client/file2.cpp',
                     'change': '',
                     'action': '',
                     'headTime': 4321,
                     'headChange': 1,
                     'path': '/path/to/file1.cpp',
                     'depotFile': '/depot/file2.cpp',
                     'headRev': 1}

        self.assertEqual(expected2, result[1])

    def test_raw_result(self):
        p4 = p4lib.P4()

        change_stdout(FSTAT_OUTPUT)

        raw_result = p4.fstat(files="/depot/test.txt", _raw=True)[1]

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(FSTAT_OUTPUT, raw_result['stdout'])
        self.assertEqual("", raw_result['stderr'])
        self.assertEqual(0, raw_result['retval'])

    def test_with_options(self):
        test_options(self, "fstat", files="/depot/test.txt",
                     expected=["fstat", "-C", "-P", "/depot/test.txt"])
