import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


LABELS_OUTPUT = """Label label_1 2002/03/18 'A first label'
Label label_2 2014/11/28 'A second label'
"""


class LabelsTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(LABELS_OUTPUT)
        self.p4 = p4lib.P4()

    def test_fills_results(self):
        result = self.p4.labels()

        p4lib._run.assert_called_with(['p4', 'labels'])

        self.assertEqual(2, len(result))

        expected_1 = {'label': 'label_1',
                      'description': 'A first label',
                      'update': '2002/03/18'}
        self.assertEqual(expected_1, result[0])

        expected_2 = {'label': 'label_2',
                      'description': 'A second label',
                      'update': '2014/11/28'}
        self.assertEqual(expected_2, result[1])

    def test_raw_result(self):
        test_raw_result(self, LABELS_OUTPUT, "labels")

    def test_with_options(self):
        test_options(self, "labels",
                     expected=["labels"])
