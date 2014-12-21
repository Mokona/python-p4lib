import unittest
import p4lib
from unittest.mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


SYNC_OUTPUT = r"""//depot/foo#1 - updating /depot/foo
//depot/bar#2 - is opened and not being changed
//depot/foo#1 - is opened at a later revision - not changed
//depot/foo#1 - deleted as /depot/foo
... //depot/foo - must resolve #2 before submitting"""


class SyncTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_returns_file_dict(self):
        change_stdout(SYNC_OUTPUT)

        p4 = p4lib.P4()

        result = p4.sync()
        p4lib._run.assert_called_with(['p4', 'sync'])

        self.assertEqual(4, len(result))

        first = result[0]
        self.assertEqual("//depot/foo", first["depotFile"])
        self.assertEqual(1, first["rev"])
        self.assertEqual("updating /depot/foo", first["comment"])
        self.assertEqual([], first["notes"])

        second = result[1]
        self.assertEqual("//depot/bar", second["depotFile"])
        self.assertEqual(2, second["rev"])
        self.assertEqual("is opened and not being changed", second["comment"])
        self.assertEqual([], second["notes"])

        third = result[2]
        self.assertEqual("//depot/foo", third["depotFile"])
        self.assertEqual(1, third["rev"])
        self.assertEqual("is opened at a later revision - not changed",
                         third["comment"])
        self.assertEqual([], third["notes"])

        fourth = result[3]
        self.assertEqual("//depot/foo", fourth["depotFile"])
        self.assertEqual(1, fourth["rev"])
        self.assertEqual("deleted as /depot/foo", fourth["comment"])
        self.assertEqual(["must resolve #2 before submitting"],
                         fourth["notes"])

    def test_uses_file_list(self):
        change_stdout(SYNC_OUTPUT)

        p4 = p4lib.P4()

        p4.sync(["f1", "f2"])
        p4lib._run.assert_called_with(['p4', 'sync', 'f1', 'f2'])

    def test_can_specify_force(self):
        change_stdout(SYNC_OUTPUT)

        p4 = p4lib.P4()

        p4.sync(force=True)
        p4lib._run.assert_called_with(['p4', 'sync', '-f'])
        
    def test_can_specify_dryrun(self):
        change_stdout(SYNC_OUTPUT)

        p4 = p4lib.P4()

        p4.sync(dryrun=True)
        p4lib._run.assert_called_with(['p4', 'sync', '-n'])

    def test_raw_result(self):
        test_raw_result(self, SYNC_OUTPUT, "sync")

    def test_with_options(self):
        test_options(self, "sync", expected=["sync"])
