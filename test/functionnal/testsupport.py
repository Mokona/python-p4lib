#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""
    px/p4lib.py test suite configuration and support routines
"""

import os
import sys
import types


#---- Configuration

tmp = 'tmp'                 # The temporary working dir for a test run.
p4port = 'localhost:6661'   # Port on which the test server will run.
p4root = os.path.join(tmp, 'repository')    # Test server repo dir.

# It is intended that the individual tests work as two perforce users:
# Andrew and Bertha, for which client views have been setup.
users = {
    'andrew': {
        'home': os.path.join(tmp, 'andrew'),
        'client': 'andrew-test',
    },
    'bertha': {
        'home': os.path.join(tmp, 'bertha'),
        'client': 'bertha-test',
    },
}


#---- Support routines

def _escapeArg(arg):
    """Escape the given command line argument for the shell."""
    #XXX There is a *lot* more that we should escape here.
    return arg.replace('"', r'\"')


def _joinArgv(argv):
    r"""Join an arglist to a string appropriate for running.
        >>> import os
        >>> _joinArgv(['foo', 'bar "baz'])
        'foo "bar \\"baz"'
    """
    cmdstr = ""
    for arg in argv:
        if ' ' in arg:
            cmdstr += '"%s"' % _escapeArg(arg)
        else:
            cmdstr += _escapeArg(arg)
        cmdstr += ' '
    if cmdstr.endswith(' '): cmdstr = cmdstr[:-1]  # strip trailing space
    return cmdstr


def run(argv):
    """Prepare and run the given arg vector, 'argv', and return the
    results.  Returns (<stdout lines>, <stderr lines>, <return value>).
    Note: 'argv' may also just be the command string.
    """
    if type(argv) in (types.ListType, types.TupleType):
        cmd = _joinArgv(argv)
    else:
        cmd = argv
    if sys.platform.startswith('win'):
        i, o, e = os.popen3(cmd)
        output = o.readlines()
        error = e.readlines()
        i.close()
        e.close()
        retval = o.close()
    else:
        import popen2
        p = popen2.Popen3(cmd, 1)
        i, o, e = p.tochild, p.fromchild, p.childerr
        output = o.readlines()
        error = e.readlines()
        i.close()
        o.close()
        e.close()
        retval = p.wait() >> 8
    return output, error, retval

