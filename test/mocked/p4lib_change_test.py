import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, change_stdout_list
from p4lib_opened_test import PX_AND_PX2_DEFAULT_CHANGE


TEMPORARY_FILENAME = "tempFile"
CHANGELIST_DESCRIPTION = "A description"

CHANGE_CREATED = r"Change 1234 created."
WHERE_RESULT = r"//depot/foo/file.py //trent/foo/file.py c:\trent\foo\file.py"


class ChangeTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')

    def __assert_change_for_creation(self, result):
        p4lib._run.assert_called_with(['p4',
                                       'change',
                                       '-i',
                                       '<',
                                       TEMPORARY_FILENAME])

        self.assertIn("change", result)
        self.assertEqual(1234, result["change"])
        self.assertIn("action", result)
        self.assertEqual("created", result["action"])

    def __get_form(self):
        args, _ = p4lib._writeTemporaryForm.call_args
        return args[0]

    def test_creates_a_change_for_no_file(self):
        change_stdout(CHANGE_CREATED)

        p4 = p4lib.P4()

        result = p4.change(files=[], description=CHANGELIST_DESCRIPTION)

        self.__assert_change_for_creation(result)

        form = self.__get_form()
        self.assertIn("Change:\tnew", form)
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertNotIn("//depot/apps/px/px.py", form)
        self.assertNotIn("//depot/apps/px/px2.py", form)

    def test_creates_a_change_without_specified_file(self):
        change_stdout_list([PX_AND_PX2_DEFAULT_CHANGE, CHANGE_CREATED])

        p4 = p4lib.P4()

        result = p4.change(description="A description")

        self.__assert_change_for_creation(result)

        form = self.__get_form()
        self.assertIn("Change:\tnew", form)
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertIn("//depot/apps/px/px.py", form)
        self.assertIn("//depot/apps/px/px2.py", form)

    def test_creates_a_change_with_specified_file(self):
        change_stdout_list([WHERE_RESULT, CHANGE_CREATED])

        p4 = p4lib.P4()

        result = p4.change(files=["//depot/foo/file.py"],
                           description=CHANGELIST_DESCRIPTION)

        self.__assert_change_for_creation(result)

        form = self.__get_form()
        self.assertIn("Change:\tnew", form)
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertIn("//depot/foo/file.py", form)

