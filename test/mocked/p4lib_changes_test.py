import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout


CHANGES_SHORT = \
    """Change 1234 on 2002/05/08 by mtrent@local *pending* 'a message'
Change 4567 on 2002/05/09 by mokona@other 'another message'"""

CHANGES_LONG = \
    """Change 1234 on 2002/05/08 by mtrent@local
\tThis is a long description.

\tWith a lot of text.

Change 4567 on 2002/05/09 by mokona@other
\tAnd another.
"""


class ChangesTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_gets_all_changes_by_default(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()

        result = p4.changes()
        p4lib._run.assert_called_with(['p4', 'changes'])

        self.assertEqual(2, len(result))

        first = result[0]
        self.assertEqual("2002/05/08", first["date"])
        self.assertEqual("local", first["client"])
        self.assertEqual("mtrent", first["user"])
        self.assertEqual(1234, first["change"])
        self.assertEqual("a message", first["description"])

        second = result[1]
        self.assertEqual("2002/05/09", second["date"])
        self.assertEqual("other", second["client"])
        self.assertEqual("mokona", second["user"])
        self.assertEqual(4567, second["change"])
        self.assertEqual("another message", second["description"])

    def test_uses_file_list(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()

        p4.changes(["f1", "f2"])
        p4lib._run.assert_called_with(['p4', 'changes', 'f1', 'f2'])

    def test_uses_follow_integrations(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()

        p4.changes(followIntegrations=True)
        p4lib._run.assert_called_with(['p4', 'changes', '-i'])

    def test_can_specify_max_result(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()

        p4.changes(max=1)
        p4lib._run.assert_called_with(['p4', 'changes', '-m', '1'])

    def test_max_must_be_integer(self):
        p4 = p4lib.P4()

        self.assertRaises(p4lib.P4LibError, p4.changes, max="")

    def test_can_specify_status(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()

        p4.changes(status="pending")
        p4lib._run.assert_called_with(['p4', 'changes', '-s', 'pending'])

        p4lib._run.reset_mock()

        p4.changes(status="submitted")
        p4lib._run.assert_called_with(['p4', 'changes', '-s', 'submitted'])

        p4lib._run.reset_mock()

        self.assertRaises(p4lib.P4LibError, p4.changes, status="nothing")

    def test_can_specify_long_output(self):
        change_stdout(CHANGES_LONG)

        p4 = p4lib.P4()

        p4.changes(longOutput=True)
        p4lib._run.assert_called_with(['p4', 'changes', '-l'])

    def test_raw_result(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()
        raw_result = p4.changes(_raw=True)

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(CHANGES_SHORT, raw_result['stdout'])

    def test_with_options(self):
        change_stdout(CHANGES_SHORT)

        p4 = p4lib.P4()
        p4.changes(user='other')

        p4lib._run.assert_called_with(['p4',
                                       '-u',
                                       'other',
                                       'changes'])
