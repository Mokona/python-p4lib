import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, change_stdout_list, test_raw_option


TEMPORARY_FILENAME = "tempFile"
CHANGELIST_DESCRIPTION = "A description"
CHANGELIST_NEW_DESCRIPTION = "A new description"

CHANGE_CREATED = r"Change 1234 created."
CHANGE_UPDATED = r"Change 1234 updated."
CHANGE_UPDATED_WITH_COMMENTS = r"Change 1234 updated, and blah."
CHANGE_DELETED = r"Change 1234 deleted."
CHANGE_INFORMATION = """Change:\t1234
Date:\t2002/05/08 23:24:54
User:\ttrent
Status:\tpending
Description:
\tA description

Files:
\t//depot/file.txt\t# edit
"""

WHERE_RESULT = r"//depot/foo/file.py //trent/foo/file.py c:\trent\foo\file.py"


class ChangeTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))
        p4lib._writeTemporaryForm = Mock(spec='p4lib._writeTemporaryForm',
                                         return_value=TEMPORARY_FILENAME)
        p4lib._removeTemporaryForm = Mock(spec='p4lib._removeTemporaryForm')

    def __assert_called_with_tempfile(self):
        p4lib._run.assert_called_with(['p4',
                                       'change',
                                       '-i',
                                       '<',
                                       TEMPORARY_FILENAME])

    def __assert_change_for_creation(self, result):
        self.__assert_called_with_tempfile()

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
        change_stdout(CHANGE_CREATED)

        p4 = p4lib.P4()

        p4.opened = Mock(spec='p4.opened',
                         return_value=[
                             {"depotFile": "//depot/apps/px/px.py"},
                             {"depotFile": "//depot/apps/px/px2.py"}])

        result = p4.change(description="A description")

        self.__assert_change_for_creation(result)
        p4.opened.assert_called_with()

        form = self.__get_form()
        self.assertIn("Change:\tnew", form)
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertIn("//depot/apps/px/px.py", form)
        self.assertIn("//depot/apps/px/px2.py", form)

    def test_creates_a_change_with_specified_file(self):
        change_stdout(CHANGE_CREATED)

        filename = r"//depot/foo/file.py"

        p4 = p4lib.P4()

        p4.where = Mock(spec='p4.opened',
                        return_value=[
                            {"depotFile": filename}])

        result = p4.change(files=[filename],
                           description=CHANGELIST_DESCRIPTION)

        self.__assert_change_for_creation(result)
        p4.where.assert_called_with([filename])

        form = self.__get_form()
        self.assertIn("Change:\tnew", form)
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertIn(filename, form)

    def test_can_get_information(self):
        change_stdout(CHANGE_INFORMATION)

        p4 = p4lib.P4()

        result = p4.change(change=1234)
        p4lib._run.assert_called_with(['p4', 'change', '-o', '1234'])

        self.assertEqual(1234, result["change"])
        self.assertEqual("pending", result["status"])
        self.assertEqual(CHANGELIST_DESCRIPTION, result["description"])
        self.assertEqual("trent", result["user"])
        self.assertEqual("2002/05/08 23:24:54", result["date"])

    def test_can_change_description(self):
        # Cannot mock change here for the internal call
        change_stdout_list([CHANGE_INFORMATION, CHANGE_UPDATED])

        p4 = p4lib.P4()

        result = p4.change(change=1234,
                           description=CHANGELIST_NEW_DESCRIPTION)

        self.__assert_called_with_tempfile()

        self.assertEqual("updated", result["action"])
        self.assertEqual(1234, result["change"])

        form = self.__get_form()
        self.assertIn(CHANGELIST_NEW_DESCRIPTION, form)

    def test_can_change_files(self):
        # Cannot mock change here for the internal call
        change_stdout_list([CHANGE_INFORMATION,
                            CHANGE_UPDATED_WITH_COMMENTS])

        filename = r"//depot/foo/file.py"

        p4 = p4lib.P4()

        p4.where = Mock(spec='p4.opened',
                        return_value=[
                            {"depotFile": filename}])

        result = p4.change(change=1234,
                           files=[filename])

        self.__assert_called_with_tempfile()
        p4.where.assert_called_with([filename])

        self.assertEqual("updated", result["action"])
        self.assertEqual(1234, result["change"])
        self.assertEqual("and blah", result["comment"])

        form = self.__get_form()
        self.assertIn(CHANGELIST_DESCRIPTION, form)
        self.assertIn("//depot/foo/file.py", form)

    def test_can_be_deleted(self):
        change_stdout(CHANGE_DELETED)

        p4 = p4lib.P4()

        result = p4.change(change=1234, delete=True)

        p4lib._run.assert_called_with(['p4', 'change', '-d', '1234'])

        self.assertEqual("deleted", result["action"])
        self.assertEqual(1234, result["change"])

    def test_cannot_specify_delete_with_files_or_description(self):
        p4 = p4lib.P4()

        self.assertRaises(p4lib.P4LibError, p4.change,
                          change=1234,
                          delete=True,
                          files=[])

        self.assertRaises(p4lib.P4LibError, p4.change,
                          change=1234,
                          delete=True,
                          descritpion="")

    def test_raw_result(self):
        change_stdout(CHANGE_DELETED)

        p4 = p4lib.P4()
        raw_result = p4.change(change=1234, delete=True, _raw=True)

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(CHANGE_DELETED, raw_result['stdout'])

    def test_with_options(self):
        change_stdout(CHANGE_DELETED)
        test_raw_option(self, "change", change=1234, delete=True,
                        expected=["change", "-d", "1234"])
