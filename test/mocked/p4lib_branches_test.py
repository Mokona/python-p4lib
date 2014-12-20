import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


BRANCHES_OUTPUT = """Branch branch_1 2002/03/18 'A first branch'
Branch branch_2 2014/11/28 'A second branch'
"""

WRONG_OUTPUT = """Nothing really to parse..."""


class BranchesTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(BRANCHES_OUTPUT)
        self.p4 = p4lib.P4()

    def test_fills_results(self):
        result = self.p4.branches()

        p4lib._run.assert_called_with(['p4', 'branches'])

        self.assertEqual(2, len(result))

        expected_1 = {'branch': 'branch_1',
                      'description': 'A first branch',
                      'update': '2002/03/18'}
        self.assertEqual(expected_1, result[0])

        expected_2 = {'branch': 'branch_2',
                      'description': 'A second branch',
                      'update': '2014/11/28'}
        self.assertEqual(expected_2, result[1])

    def test_raises_if_cannot_parse(self):
        change_stdout(WRONG_OUTPUT)
        self.assertRaises(p4lib.P4LibError, self.p4.branches)

    def test_raw_result(self):
        test_raw_result(self, BRANCHES_OUTPUT, "branches")

    def test_with_options(self):
        test_options(self, "branches",
                     expected=["branches"])
