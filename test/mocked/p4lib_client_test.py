import unittest
import p4lib
from unittest.mock import Mock
from test_utils import change_stdout, change_stdout_list
from test_utils import test_raw_result, test_options


TEMPORARY_FILENAME = "tempFile"

CLIENT_UPDATE_OUTPUT = "Client bertha-test saved."

CLIENT_DELETE_OUTPUT = "Client bertha-test deleted."

CLIENT_GET_OUTPUT = """Client: trentm-ra
Access: 2002/07/16 00:05:31
Description:
\tCreated by trentm

Host: ra
Owner: trentm
"""

CLIENT_DICTIONARY = {'access': '2002/07/16 00:05:31',
                     'client': 'trentm-ra',
                     'description': 'Created by trentm.',
                     'host': 'ra',
                     'lineend': 'local',
                     'options': 'noallwrite noclobber',
                     'owner': 'trentm',
                     'root': 'c:\\trentm\\',
                     'update': '2002/03/18 22:33:18',
                     'view': '//depot/... //trentm-ra/...'}

CLIENT_NEW_DICT = {'description': 'Created by trentm.',
                   'host': 'ra',
                   'lineend': 'local',
                   'options': 'noallwrite noclobber',
                   'owner': 'trentm',
                   'root': 'c:\\trentm\\',
                   'view': '//depot/... //trentm-ra/...'}


class ClientTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')

        self.p4 = p4lib.P4()

    def __assert_called_with_tempfile(self):
        p4lib._run.assert_called_with(['p4',
                                       'client',
                                       '-i',
                                       '<',
                                       TEMPORARY_FILENAME])

    def test_can_update_a_client(self):
        """ The client is specified in the DICTIONARY. """
        change_stdout_list([CLIENT_GET_OUTPUT, CLIENT_UPDATE_OUTPUT])

        result = self.p4.client(client=CLIENT_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'client': 'bertha-test'}
        self.assertEqual(expected, result)

    def test_can_update_a_client_2(self):
        """ The client is specified in the call. """
        change_stdout_list([CLIENT_GET_OUTPUT, CLIENT_UPDATE_OUTPUT])

        result = self.p4.client(name='client-name', client=CLIENT_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'client': 'bertha-test'}
        self.assertEqual(expected, result)

    def test_can_create_a_new_client(self):
        change_stdout(CLIENT_UPDATE_OUTPUT)

        result = self.p4.client(client=CLIENT_NEW_DICT)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'client': 'bertha-test'}
        self.assertEqual(expected, result)

    def test_can_get_client_specs(self):
        change_stdout(CLIENT_GET_OUTPUT)

        result = self.p4.client(name='client-name')

        p4lib._run.assert_called_with(['p4',
                                       'client',
                                       '-o',
                                       'client-name'])

        expected_1 = {'access': '2002/07/16 00:05:31',
                      'owner': 'trentm',
                      'host': 'ra',
                      'client': 'trentm-ra',
                      'description': 'Created by trentm'}

        self.assertEqual(expected_1, result)

    def test_can_delete_a_client(self):
        change_stdout(CLIENT_DELETE_OUTPUT)

        result = self.p4.client(name='client-name', delete=True)

        p4lib._run.assert_called_with(['p4',
                                       'client',
                                       '-d',
                                       'client-name'])

        expected = {'action': 'deleted', 'client': 'bertha-test'}
        self.assertEqual(expected, result)

    def test_has_forbidden_parameter_combinations(self):
        self.assertRaises(p4lib.P4LibError, self.p4.client)
        self.assertRaises(p4lib.P4LibError, self.p4.client, delete=True)

    def test_raw_result(self):
        test_raw_result(self, CLIENT_GET_OUTPUT, "client", name="client-name")

    def test_with_options(self):
        test_options(self, "client", name='client-name',
                     expected=["client", "-o", "client-name"])
