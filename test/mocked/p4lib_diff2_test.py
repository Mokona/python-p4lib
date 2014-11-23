import unittest


""" diff2 implementation is using popen3 and marshalling.

It's complicated to mock and uses a marshalling version.

Probably needs to reimplement it with the -s option (see source code)
"""


class Diff2TestCase(unittest.TestCase):
    @unittest.skip("Reimplement diff2")
    def test_no_test(self):
        pass
