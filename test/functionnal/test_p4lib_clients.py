#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 clients'."""

import os
import unittest

import testsupport
from p4lib import P4


class ClientsTestCase(unittest.TestCase):
    def test_get_clients(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()

        try:
            os.chdir(andrew['home'])

            clients = p4.clients()
            for client in clients:
                self.failUnless('client' in client)
                self.failUnless('update' in client)
                self.failUnless('root' in client)
                self.failUnless('description' in client)
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(ClientsTestCase)

