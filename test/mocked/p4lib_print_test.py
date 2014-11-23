import unittest


""" print_ implementation is using popen3 and marshalling.

It's complicated to mock and uses a marshalling version.

Probably needs to reimplement it with the -s option (see source code)
"""


class PrintTestCase(unittest.TestCase):
    @unittest.skip("Reimplement print_")
    def test_no_test(self):
        pass
