import unittest
import p4lib
from unittest.mock import Mock
from test_utils import change_stdout, change_stdout_list
from test_utils import test_options, test_raw_result


TEMPORARY_FILENAME = "tempFile"

BRANCH_OUTPUT = """
"""

BRANCH_UPDATE_OUTPUT = "Branch branch_1 saved."

BRANCH_DELETE_OUTPUT = "Branch branch_2 deleted."

BRANCH_GET_OUTPUT = """Branch: branch_3
Access: 2002/07/16 00:05:31
Description:
\tCreated by trentm

Options: unlocked
Owner: trentm
"""

BRANCH_DICTIONARY = {'access': '2002/07/16 00:05:31',
                     'branch': 'trentm-roundup',
                     'description': 'Branch ...',
                     'options': 'unlocked',
                     'owner': 'trentm',
                     'update': '2000/12/01 16:54:57',
                     'view': '//depot/foo/... //depot/bar...'}

BRANCH_NEW_DICTIONARY = {'description': 'Branch ...',
                         'options': 'unlocked',
                         'owner': 'trentm',
                         'view': '//depot/foo/... //depot/bar...'}


class BranchTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')

        change_stdout(BRANCH_OUTPUT)
        self.p4 = p4lib.P4()

    def __assert_called_with_tempfile(self):
        p4lib._run.assert_called_with(['p4',
                                       'branch',
                                       '-i',
                                       '<',
                                       TEMPORARY_FILENAME])

    def test_can_update_a_branch_1(self):
        """ The client is specified in the DICTIONARY. """
        change_stdout_list([BRANCH_GET_OUTPUT, BRANCH_UPDATE_OUTPUT])

        result = self.p4.branch(branch=BRANCH_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'branch': 'branch_1'}
        self.assertEqual(expected, result)

    def test_can_update_a_branch_2(self):
        """ The client is specified in the call. """
        change_stdout_list([BRANCH_GET_OUTPUT, BRANCH_UPDATE_OUTPUT])

        result = self.p4.branch(name="branch-name", branch=BRANCH_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'branch': 'branch_1'}
        self.assertEqual(expected, result)

    def test_can_create_a_new_branch(self):
        change_stdout(BRANCH_UPDATE_OUTPUT)

        result = self.p4.branch(branch=BRANCH_NEW_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'branch': 'branch_1'}
        self.assertEqual(expected, result)

    def test_can_get_branch_specs(self):
        change_stdout(BRANCH_GET_OUTPUT)

        result = self.p4.branch(name='branch-name')

        p4lib._run.assert_called_with(['p4',
                                       'branch',
                                       '-o',
                                       'branch-name'])

        expected_1 = {'access': '2002/07/16 00:05:31',
                      'branch': 'branch_3',
                      'owner': 'trentm',
                      'options': 'unlocked',
                      'description': 'Created by trentm'}

        self.assertEqual(expected_1, result)

    def test_can_delete_a_branch(self):
        change_stdout(BRANCH_DELETE_OUTPUT)

        result = self.p4.branch(name='branch-name', delete=True)

        p4lib._run.assert_called_with(['p4',
                                       'branch',
                                       '-d',
                                       'branch-name'])

        expected = {'action': 'deleted', 'branch': 'branch_2'}
        self.assertEqual(expected, result)

    def test_has_forbidden_parameter_combinations(self):
        self.assertRaises(p4lib.P4LibError, self.p4.submit)
        self.assertRaises(p4lib.P4LibError, self.p4.submit, delete=True)

    def test_raw_result(self):
        test_raw_result(self, BRANCH_OUTPUT, "branch", name="branch_1")

    def test_with_options(self):
        test_options(self, "branch", name="branch_1",
                     expected=["branch", "-o", "branch_1"])
