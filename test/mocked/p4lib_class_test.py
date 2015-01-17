import unittest
import p4lib
from mock23 import Mock


class P4LibTestCase(unittest.TestCase):
    def setUp(self):
        p4lib._run = Mock(spec='p4lib._run', return_value=("", "", 0))

    def test_initilization(self):
        p4 = p4lib.P4()
        self.assertEqual('p4', p4.p4)
