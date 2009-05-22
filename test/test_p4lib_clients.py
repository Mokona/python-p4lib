#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""Test p4lib.py's interface to 'p4 clients'."""

import os
import sys
import unittest
import pprint

import testsupport
from p4lib import P4, P4LibError


class ClientsTestCase(unittest.TestCase):
    def test_get_clients(self):
        top = os.getcwd()
        andrew = testsupport.users['andrew']
        p4 = P4()

        try:
            os.chdir(andrew['home'])

            clients = p4.clients()
            for client in clients:
                self.failUnless(client.has_key('client'))
                self.failUnless(client.has_key('update'))
                self.failUnless(client.has_key('root'))
                self.failUnless(client.has_key('description'))
        finally:
            os.chdir(top)


def suite():
    """Return a unittest.TestSuite to be used by test.py."""
    return unittest.makeSuite(ClientsTestCase)

