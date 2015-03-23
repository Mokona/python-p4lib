import unittest
import p4lib
from mock23 import Mock
from test_utils import change_stdout, test_options, test_raw_result


CHANGE_NUM = 1234
USER = "someuser"
CLIENT = "someclient"
DATE = "2014/11/01"
DESCRIPTION = "Some changelist description"
FILE_0 = "//depot/file.cpp"
REV_0 = 3
ACTION_0 = "edit"
FILE_1 = "//depot/file2.cpp"
REV_1 = 4
ACTION_1 = "edit"


DESCRIBE_OUTPUT_BASE = """Change %i by %s@%s on %s

\t%s

Affected files ...

... %s#%i %s
... %s#%i %s
""" % (CHANGE_NUM, USER, CLIENT, DATE,
       DESCRIPTION,
       FILE_0, REV_0, ACTION_0,
       FILE_1, REV_1, ACTION_1)

DESCRIBE_OUTPUT = DESCRIBE_OUTPUT_BASE + """
"""

DESCRIBE_OUTPUT_LONG = DESCRIBE_OUTPUT_BASE + """
Differences ...

==== //depot/apps/px/ReadMe.txt#5 (text/utf8) ====
DiffLine1

"""

DESCRIBE_OUTPUT_MOVE_DELETE = DESCRIBE_OUTPUT_BASE + """
Moved files ...

... //depot/file1.cpp#1 moved from ... //depot/file2.cpp#1

Differences ...

"""


class DescribeTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def _common_asserts(self, result):
        self.assertEqual(CHANGE_NUM, result["change"])
        self.assertEqual(DESCRIPTION, result["description"])
        self.assertEqual(USER, result["user"])
        self.assertEqual(CLIENT, result["client"])
        self.assertIn("files", result)

        files = result["files"]
        self.assertEqual(2, len(files))

        file_0 = files[0]
        self.assertEqual(FILE_0, file_0["depotFile"])
        self.assertEqual(REV_0, file_0["rev"])
        self.assertEqual(ACTION_0, file_0["action"])

        file_1 = files[1]
        self.assertEqual(FILE_1, file_1["depotFile"])
        self.assertEqual(REV_1, file_1["rev"])
        self.assertEqual(ACTION_1, file_1["action"])

    def test_with_change_short_form(self):
        change_stdout(DESCRIBE_OUTPUT)

        p4 = p4lib.P4()

        result = p4.describe(change=CHANGE_NUM, shortForm=True)
        p4lib._run.assert_called_with(['p4', 'describe', '-s', '1234'])

        self._common_asserts(result)
        self.assertNotIn("diff", result)

    def test_with_change_long_form(self):
        change_stdout(DESCRIBE_OUTPUT_LONG)

        p4 = p4lib.P4()

        result = p4.describe(change=CHANGE_NUM)
        p4lib._run.assert_called_with(['p4', 'describe', '1234'])

        self._common_asserts(result)
        self.assertIn("diff", result)

    def test_with_change_long_form_with_move_delete(self):
        change_stdout(DESCRIBE_OUTPUT_MOVE_DELETE)

        p4 = p4lib.P4()

        result = p4.describe(change=CHANGE_NUM)
        p4lib._run.assert_called_with(['p4', 'describe', '1234'])

        self._common_asserts(result)
        self.assertIn("diff", result)

    def test_raw_result(self):
        test_raw_result(self, DESCRIBE_OUTPUT_LONG, "describe",
                        change=CHANGE_NUM)

        p4 = p4lib.P4()

        result = p4.describe(change=CHANGE_NUM)
        self._common_asserts(result)

    def test_with_options(self):
        change_stdout(DESCRIBE_OUTPUT_LONG)
        test_options(self, "describe", change=CHANGE_NUM,
                     expected=["describe", "1234"])
