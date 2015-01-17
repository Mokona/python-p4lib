import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, change_stdout_list
from test_utils import test_options, test_raw_result

TEMPORARY_FILENAME = "tempFile"

LABEL_UPDATE_OUTPUT = "Label label_1 saved."

LABEL_DELETE_OUTPUT = "Label label_2 deleted."

LABEL_GET_OUTPUT = """Label: ActivePerl_623
Access: 2002/07/16 00:05:31
Description:
\tActivePerl 623

Owner: trentm
"""

LABEL_DICTIONARY = {'access': '2002/07/16 00:05:31',
                    'description': 'ActivePerl 623',
                    'label': 'ActivePerl_623',
                    'options': 'locked',
                    'owner': 'daves',
                    'update': '2002/03/18 22:33:18',
                    'view': '//depot/main/Apps/ActivePerl/...'}

LABEL_NEW_DICT = {'access': '2002/07/16 00:05:31',
                  'description': 'ActivePerl 623',
                  'options': 'locked',
                  'owner': 'daves',
                  'update': '2002/03/18 22:33:18',
                  'view': '//depot/main/Apps/ActivePerl/...'}


class LabelTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')
        self.p4 = p4lib.P4()

    def __assert_called_with_tempfile(self):
        p4lib._run.assert_called_with(['p4',
                                       'label',
                                       '-i',
                                       '<',
                                       TEMPORARY_FILENAME])

    def test_can_update_a_label(self):
        """ The label is specified in the DICTIONARY. """
        change_stdout_list([LABEL_GET_OUTPUT, LABEL_UPDATE_OUTPUT])

        result = self.p4.label(label=LABEL_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'label': 'label_1'}
        self.assertEqual(expected, result)

    def test_can_update_a_label_2(self):
        """ The label is specified in the call. """
        change_stdout_list([LABEL_GET_OUTPUT, LABEL_UPDATE_OUTPUT])

        result = self.p4.label(name='label-name', label=LABEL_DICTIONARY)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'label': 'label_1'}
        self.assertEqual(expected, result)

    def test_can_create_a_new_label(self):
        change_stdout(LABEL_UPDATE_OUTPUT)

        result = self.p4.label(label=LABEL_NEW_DICT)
        self.__assert_called_with_tempfile()

        expected = {'action': 'saved', 'label': 'label_1'}
        self.assertEqual(expected, result)

    def test_can_get_label_specs(self):
        change_stdout(LABEL_GET_OUTPUT)

        result = self.p4.label(name='label-name')

        p4lib._run.assert_called_with(['p4',
                                       'label',
                                       '-o',
                                       'label-name'])

        expected_1 = {'access': '2002/07/16 00:05:31',
                      'label': 'ActivePerl_623',
                      'owner': 'trentm',
                      'description': 'ActivePerl 623'}

        self.assertEqual(expected_1, result)

    def test_can_delete_a_label(self):
        change_stdout(LABEL_DELETE_OUTPUT)

        result = self.p4.label(name='label-name', delete=True)

        p4lib._run.assert_called_with(['p4',
                                       'label',
                                       '-d',
                                       'label-name'])

        expected = {'action': 'deleted', 'label': 'label_2'}
        self.assertEqual(expected, result)

    def test_has_forbidden_parameter_combinations(self):
        self.assertRaises(p4lib.P4LibError, self.p4.label)
        self.assertRaises(p4lib.P4LibError, self.p4.label, delete=True)

    def test_raw_result(self):
        test_raw_result(self, LABEL_GET_OUTPUT, "label", name='label-name')

    def test_with_options(self):
        test_options(self, "label", name='label-name',
                     expected=["label", "-o", "label-name"])
