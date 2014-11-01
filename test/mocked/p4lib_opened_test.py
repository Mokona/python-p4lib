import unittest
import p4lib
from mock import Mock
from test_utils import change_stdout


PX_DEFAULT_CHANGE = "//depot/apps/px/px.py#3 - edit default change (text)"
PX_AND_PX2_DEFAULT_CHANGE = """//depot/apps/px/px.py#3 - edit default change (text)
//depot/apps/px/px2.py#4 - edit default change (text)
"""

NO_FILE_OPENED = "//depot/apps/px/px.py#3 - file(s) not opened on this client."


class OpenedTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_global(self):
        change_stdout(PX_DEFAULT_CHANGE)

        p4 = p4lib.P4()
        result_files = p4.opened()

        p4lib._run.assert_called_with(['p4', 'opened'])
        self.assertEqual(1, len(result_files))

        expected = {'rev': 3,
                    'action': 'edit',
                    'type': 'text',
                    'depotFile': '//depot/apps/px/px.py',
                    'change': 'default'}
        self.assertEqual(expected, result_files[0])

    def test_opened_allclients(self):
        change_stdout("//depot/foo.txt#1 - edit change 123 (text+w) by tm@tmc")

        p4 = p4lib.P4()
        result_files = p4.opened(allClients=True)

        p4lib._run.assert_called_with(['p4', 'opened', '-a'])
        self.assertEqual(1, len(result_files))

        expected = {'rev': 1,
                    'action': 'edit',
                    'type': 'text+w',
                    'depotFile': '//depot/foo.txt',
                    'change': 123,
                    'client': 'tmc',
                    'user': 'tm'}
        self.assertEqual(expected, result_files[0])

    def test_opened_file(self):
        change_stdout(PX_DEFAULT_CHANGE)

        p4 = p4lib.P4()
        result_files = p4.opened(files='//depot/apps/px/px.py')

        p4lib._run.assert_called_with(['p4',
                                       'opened',
                                       '//depot/apps/px/px.py'])
        self.assertEqual(1, len(result_files))

    def test_opened_file_as_list(self):
        change_stdout(PX_AND_PX2_DEFAULT_CHANGE)

        p4 = p4lib.P4()
        result_files = p4.opened(files=['//depot/apps/px/px.py',
                                        '//depot/apps/px/px2.py'])

        p4lib._run.assert_called_with(['p4',
                                       'opened',
                                       '//depot/apps/px/px.py',
                                       '//depot/apps/px/px2.py'])
        self.assertEqual(2, len(result_files))

    def test_opened_file_as_list_raw_result(self):
        change_stdout(PX_AND_PX2_DEFAULT_CHANGE)

        p4 = p4lib.P4()
        raw_result = p4.opened(files=['//depot/apps/px/px.py',
                                      '//depot/apps/px/px2.py'],
                               _raw=True)

        p4lib._run.assert_called_with(['p4',
                                       'opened',
                                       '//depot/apps/px/px.py',
                                       '//depot/apps/px/px2.py'])

        self.assertIn('stdout', raw_result)
        self.assertIn('stderr', raw_result)
        self.assertIn('retval', raw_result)

        self.assertEqual(PX_AND_PX2_DEFAULT_CHANGE, raw_result['stdout'])

    def test_opened_with_options(self):
        change_stdout(PX_DEFAULT_CHANGE)

        p4 = p4lib.P4()
        p4.opened(files='//depot/apps/px/px.py',
                  user='other')

        p4lib._run.assert_called_with(['p4',
                                       '-u',
                                       'other',
                                       'opened',
                                       '//depot/apps/px/px.py'])

    @unittest.skip('WOuld not pass on latest stable version.')
    def test_no_opened_file(self):
        change_stdout(NO_FILE_OPENED)

        p4 = p4lib.P4()
        result_files = p4.opened(files='//depot/apps/px/px.py')

        self.assertEqual(0, len(result_files))
