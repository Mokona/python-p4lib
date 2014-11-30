import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout, test_options, test_raw_result


EDIT_OUTPUT_1 = r"//depot/test.cpp#3 - currently opened for edit"

EDIT_OUTPUT_2 = r"""//depot/build.py#142 - opened for edit
... //depot/build.py - must sync/resolve #143,#148 before submitting
... //depot/build.py - also opened by davida@davida-bertha
... //depot/build.py - also opened by davida@davida-loom
... //depot/build.py - also opened by davida@davida-marteau
... //depot/build.py - also opened by trentm@trentm-razor
//depot/test.cpp#3 - currently opened for edit
"""

EDIT_FILENAME = "//depot/test.cpp"
EDIT_FILENAMES = ["//depot/build.py", "//depot/test.cpp"]


class EditTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_a_file(self):
        change_stdout(EDIT_OUTPUT_1)

        p4 = p4lib.P4()

        result = p4.edit(EDIT_FILENAME)

        p4lib._run.assert_called_with(['p4', 'edit', EDIT_FILENAME])

        self.assertEqual(1, len(result))

        file_1 = result[0]

        self.assertIn('depotFile', file_1)
        self.assertIn('rev', file_1)
        self.assertIn('comment', file_1)
        self.assertIn('notes', file_1)

        self.assertEqual(EDIT_FILENAME, file_1['depotFile'])
        self.assertEqual('3', file_1['rev'])
        self.assertEqual("currently opened for edit", file_1['comment'])
        self.assertEqual([], file_1['notes'])

    def test_two_files(self):
        change_stdout(EDIT_OUTPUT_2)

        p4 = p4lib.P4()

        result = p4.edit(EDIT_FILENAMES)

        p4lib._run.assert_called_with(['p4', 'edit'] + EDIT_FILENAMES)

        self.assertEqual(2, len(result))

    def test_parse_notes(self):
        change_stdout(EDIT_OUTPUT_2)

        p4 = p4lib.P4()

        result = p4.edit(EDIT_FILENAMES)

        p4lib._run.assert_called_with(['p4', 'edit'] + EDIT_FILENAMES)

        file_1 = result[0]
        notes = file_1['notes']
        self.assertEqual(5, len(notes))

        self.assertEqual("must sync/resolve #143,#148 before submitting",
                         notes[0])
        self.assertEqual("also opened by trentm@trentm-razor", notes[4])

    def test_can_specify_filetype(self):
        change_stdout(EDIT_OUTPUT_1)

        p4 = p4lib.P4()

        p4.edit(EDIT_FILENAME, filetype='text')

        p4lib._run.assert_called_with(['p4', 'edit',
                                       '-t', 'text', EDIT_FILENAME])

    def test_can_specify_change(self):
        change_stdout(EDIT_OUTPUT_1)

        p4 = p4lib.P4()

        p4.edit(EDIT_FILENAME, change=1234)

        p4lib._run.assert_called_with(['p4', 'edit',
                                       '-c', '1234', EDIT_FILENAME])

    def test_raw_result(self):
        test_raw_result(self, EDIT_OUTPUT_1, "edit", files=EDIT_FILENAME)

    def test_with_options(self):
        test_options(self, "edit", files=EDIT_FILENAME,
                     expected=["edit", EDIT_FILENAME])
