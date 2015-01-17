import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


CLIENTS_OUTPUT = """Client trentm-ra 2002/03/18 root c:\\trentm\\ 'By trentm.'
Client mokona-local 2014/11/28 root /home/mokona/workspace 'By mokona.'
"""


class ClientsTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        change_stdout(CLIENTS_OUTPUT)
        self.p4 = p4lib.P4()

    def test_fills_results(self):
        result = self.p4.clients()

        p4lib._run.assert_called_with(['p4', 'clients'])

        self.assertEqual(2, len(result))

        expected_1 = {'client': 'trentm-ra',
                      'root': 'c:\\trentm\\',
                      'update': '2002/03/18',
                      'description': 'By trentm.'}
        self.assertEqual(expected_1, result[0])

        expected_2 = {'client': 'mokona-local',
                      'root': '/home/mokona/workspace',
                      'update': '2014/11/28',
                      'description': 'By mokona.'}
        self.assertEqual(expected_2, result[1])

    def test_raw_result(self):
        test_raw_result(self, CLIENTS_OUTPUT, "clients")

    def test_with_options(self):
        test_options(self, "clients",
                     expected=["clients"])
