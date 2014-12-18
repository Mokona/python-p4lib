import unittest
from mock import MagicMock
import p4lib


def list_to_dict(l):
    return dict(zip(l[::2], l[1::2]))


class MakeOptvTestCase(unittest.TestCase):
    def test_returns_empty_list_if_no_arguments(self):
        result = p4lib.makeOptv()
        self.assertEqual([], result)

    def test_skips_arguments_with_none_value(self):
        result = p4lib.makeOptv(no_arg=None, port=None)
        self.assertEqual([], result)

    def test_raises_on_unexpected_argument(self):
        self.assertRaises(p4lib.P4LibError,
                          p4lib.makeOptv,
                          no_arg=1,
                          password="pass")

    def test_transforms_known_arguments(self):
        result = p4lib.makeOptv(client="client",
                                dir="dir",
                                host="host",
                                port="port",
                                password="pass",
                                user="user")

        expected = {'-d': 'dir', '-c': 'client', '-H': 'host',
                    '-u': 'user', '-p': 'port', '-P': 'pass'}
        
        self.assertEqual(expected, list_to_dict(result))


class ParseOptvTestCase(unittest.TestCase):
    def test_returns_empty_dict_if_empty_string(self):
        result = p4lib.parseOptv("")
        self.assertEqual({}, result)

    def test_raises_on_inappropriate_options(self):
        self.assertRaises(p4lib.P4LibError,
                          p4lib.parseOptv,
                          ["-h"])

        self.assertRaises(p4lib.P4LibError,
                          p4lib.parseOptv,
                          ["-V"])

        self.assertRaises(p4lib.P4LibError,
                          p4lib.parseOptv,
                          ["-x", "thing"])

    def test_logs_ignored_options(self):
        p4lib.log = MagicMock()

        p4lib.parseOptv(["-G"])
        self.assertTrue(p4lib.log.info.called)

        p4lib.log.reset_mock()
        self.assertFalse(p4lib.log.info.called)

        p4lib.parseOptv(["-s"])
        self.assertTrue(p4lib.log.info.called)

    def test_transforms_known_arguments(self):
        cmdline = ['-d', 'dir', '-c', 'client', '-H', 'host',
                   '-u', 'user', '-p', 'port', '-P', 'pass']
        result = p4lib.parseOptv(cmdline)

        expected = {'host': 'host', 'client': 'client', 'user': 'user',
                    'password': 'pass', 'port': 'port', 'dir': 'dir'}
        
        self.assertEqual(expected, result)


class ValuesToIntTestCase(unittest.TestCase):
    def test_can_parse_empty_dict(self):
        self.assertEqual({}, p4lib.values_to_int({}, []))
        self.assertEqual({}, p4lib.values_to_int({}, ["key1", "key2"]))

    def test_turns_parsable_to_int(self):
        self.assertEqual({"k1": 1, "k2": 2, "k3": "3"},
                         p4lib.values_to_int({"k1": "1", "k2": "2", "k3": "3"},
                                             ["k1", "k2"]))

    def test_raises_when_not_parsable(self):
        self.assertRaises(ValueError, p4lib.values_to_int,
                          {"k1": "str", "k2": "2", "k3": "3"},
                          ["k1", "k2"])


class PruneNoneValueTestCase(unittest.TestCase):
    def test_can_parse_empty_dict(self):
        self.assertEqual({}, p4lib.prune_none_values({}))

    def test_removes_key_with_none_values(self):
        self.assertEqual({"k1": "2"},
                         p4lib.prune_none_values({"k1": "2", "k2": None}))
