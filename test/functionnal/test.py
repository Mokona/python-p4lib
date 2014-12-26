#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""
    px and p4lib.py Regression Test Suite Harness

    Usage:
        python test.py [<options>...] [<tests>...]

    Options:
        -x <testname>, --exclude=<testname>
                        Exclude the named test from the set of tests to be
                        run.  This can be used multiple times to specify
                        multiple exclusions.
        -v, --verbose   run tests in verbose mode with output to stdout
        -q, --quiet     don't print anything except if a test fails
        -h, --help      print this text and exit

    This will find all modules whose name is "test_*" in the test
    directory, and run them.  Various command line options provide
    additional facilities.

    If non-option arguments are present, they are names for tests to run.
    If no test names are given, all tests are run.

    Test Setup Options:
        --p4d=<path-to-p4d> Server executable to use for test server.
        -c, --clean     Don't setup, just clean up the test workspace.
        -n, --no-clean  Don't clean up after setting up and running the
                        test suite.

    Because this test suite intends to test scripts interfacing with
    Perforce, a test p4d server is setup (with associated test users and
    clients), before the tests are run, and shutdown and cleaned up afterwards.
"""

import os
import sys
import getopt
import glob
import time
import tempfile
import unittest
import stat

import which
import testsupport


#---- exceptions

class TestError(Exception):
    pass


#---- globals

gVerbosity = 2


#---- utility routines

def _rmtreeOnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        rmFunction(filePath)


def _rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtreeOnError)


def _getAllTests(testDir):
    """Return a list of all tests to run."""
    testPyFiles = glob.glob(os.path.join(testDir, "test_*.py"))
    modules = [f[:-3] for f in testPyFiles if f and f.endswith(".py")]

    packages = []
    for f in glob.glob(os.path.join(testDir, "test_*")):
        if os.path.isdir(f) and "." not in f:
            if os.path.isfile(os.path.join(testDir, f, "__init__.py")):
                packages.append(f)

    return modules + packages


def _getP4D():
    try:
        return which.which('p4d', path=[os.curdir])
    except which.WhichError:
        try:
            return which.which('p4d')
        except which.WhichError:
            raise TestError("cannot not find a 'p4d' Perforce server binary "
                            "to use for testing. You must download one from "
                            "http://www.perforce.com/perforce/loadprog.html "
                            "to the current directory or to somewhere on "
                            "your PATH")


def _setUp(p4d=None):
    print ("=" * 50)
    print ("Setting up test workspace.")

    # Abort if there is a server running at this port or if the tmp
    # working directory exists.
    if os.path.exists(testsupport.tmp):
        raise TestError("Intended test working dir, '%s', already exists. "
                        "Perhaps you need to run 'python test.py -c'."
                        % testsupport.tmp)
    if sys.platform.startswith('win'):
        cmd = 'p4 -u andrew -p %s info > nul 2>&1' % testsupport.p4port
    else:
        cmd = 'p4 -u andrew -p %s info > /dev/null 2>&1' % testsupport.p4port
    if not os.system(cmd):
        raise TestError("There is currently a Perforce server running at "
                        "the intended test server port, '%s'. "
                        "Perhaps you need to run 'python test.py -c'."
                        % testsupport.p4port)

    # Start the server.
    if p4d is None:
        p4d = _getP4D()
    os.makedirs(testsupport.tmp)
    os.makedirs(testsupport.p4root)
    if sys.platform.startswith('win'):
        cmd = 'start "test server" /MIN "%s" -J journal -L log -p %s -r %s'\
              % (p4d, testsupport.p4port, os.path.abspath(testsupport.p4root))
    else:
        cmd = '%s -J journal -L log -p %s -r %s &'\
              % (p4d, testsupport.p4port, os.path.abspath(testsupport.p4root))
    os.system(cmd)
    print ("Starting Perforce server with '%s'..." % cmd)
    time.sleep(1)  # Give it a second to start up.
    if gVerbosity >= 3:
        os.system('p4 -u andrew -p %s info' % testsupport.p4port)

    # Setup work spaces for each user. Use the P4CONFIG mechanism to
    # setup easy p4 usage in each home directory (use the same P4CONFIG
    # value currently in use, if any, else default to '.p4config').
    P4CONFIG = os.environ.get("P4CONFIG", None)
    if not P4CONFIG and sys.platform.startswith("win"):
        o = os.popen('p4 set P4CONFIG')
        line = o.read()
        o.close()
        if line:
            P4CONFIG = line.split()[0].split('=')[1]
    if not P4CONFIG:
        P4CONFIG = '.p4config'
        os.environ['P4CONFIG'] = P4CONFIG
    for username, user in testsupport.users.items():
        os.makedirs(user['home'])
        p4config = """\
P4PORT=%s
P4USER=%s
P4CLIENT=%s
""" % (testsupport.p4port, username, user['client'])
        open(os.path.join(user['home'], P4CONFIG), 'w').write(p4config)
        data = {'client': user['client'],
                'user': username,
                'abshome': os.path.abspath(user['home'])}
        p4client = """\
Client:	%(client)s

Owner:	%(user)s

Description:
	Created by test harness.

Root:	%(abshome)s

View:
	//depot/... //%(client)s/...
""" % data
        tmpfile = tempfile.mktemp()
        open(tmpfile, 'w').write(p4client)
        cmd = 'p4 -u andrew -p %s client -i < "%s"'\
              % (testsupport.p4port, tmpfile)
        retval = os.system(cmd)
        if retval:
            raise TestError("Problem setting up client for '%s' with '%s'."
                            % (username, cmd))

    # Put p4lib.py on sys.path and ../px.exe on the PATH.
    sys.path.insert(0, os.path.abspath(os.pardir))
    if "PATH" in os.environ:
        os.environ["PATH"] = os.path.abspath(os.pardir) + \
            os.pathsep + \
            os.environ["PATH"]
    else:
        os.environ["PATH"] = os.path.abspath(os.pardir)
    print ("Setup to test: ")
    import p4lib
    print ("\tp4lib at %r" % p4lib.__file__)
    # try:
    #     px = which.which('px')
    #     print "\tpx at %r" % px
    # except ImportError:
    #     sys.stdout.flush()
    #     os.system('px -V')

    print ("=" * 50)


def _tearDown(p4d=None):
    print ("=" * 50)
    print ("Tearing down test workspace.")
    if sys.platform.startswith('win'):
        cmd = 'p4 -u andrew -p %s info > nul 2>&1' % testsupport.p4port
    else:
        cmd = 'p4 -u andrew -p %s info > /dev/null 2>&1' % testsupport.p4port
    if not os.system(cmd):
        print ("Stopping test server on port %s." % testsupport.p4port)
        os.system('p4 -u andrew -p %s admin stop' % testsupport.p4port)
    time.sleep(1)  # Give it a second to shutdown.
    if os.path.exists(testsupport.tmp):
        print ("Removing working dir: '%s'" % testsupport.tmp)
        _rmtree(testsupport.tmp)
    print ("=" * 50)


def test(testModules, testDir=os.curdir, exclude=[]):
    """Run the given regression tests and report the results."""
    # Determine the test modules to run.
    if not testModules:
        testModules = _getAllTests(testDir)
    testModules = [t for t in testModules if t not in exclude]

    # Aggregate the TestSuite's from each module into one big one.
    allSuites = []
    for moduleFile in testModules:
        moduleFile = os.path.basename(moduleFile)

        if moduleFile in exclude:
            print ("-> Exclude: " + moduleFile)
            continue

        print ("-> Import: " + moduleFile)
        module = __import__(moduleFile, globals(), locals(), [])
        # module = importlib.import_module(moduleFile)
        suite = getattr(module, "suite", None)
        if suite is not None:
            allSuites.append(suite())
        else:
            if gVerbosity >= 2:
                print ("WARNING: module '%s' did not have a suite() method."
                       % moduleFile)
    suite = unittest.TestSuite(allSuites)

    # Run the suite.
    runner = unittest.TextTestRunner(sys.stdout, verbosity=gVerbosity)
    result = runner.run(suite)


#---- mainline

def main(argv):
    testDir = os.path.dirname(sys.argv[0])

    # parse options
    global gVerbosity
    try:
        opts, testModules = getopt.getopt(sys.argv[1:], 'hvqx:cn',
                                          ['help', 'verbose', 'quiet',
                                           'exclude=', 'p4d=', 'clean',
                                           'no-clean'])
    except getopt.error as ex:
        print ("%s: ERROR: %s" % (argv[0], ex))
        print (__doc__)
        sys.exit(2)
    exclude = []
    setupOpts = {}
    justClean = 0
    clean = 1
    for opt, optarg in opts:
        if opt in ("-h", "--help"):
            print (__doc__)
            sys.exit(0)
        elif opt in ("-v", "--verbose"):
            gVerbosity += 1
        elif opt in ("-q", "--quiet"):
            gVerbosity -= 1
        elif opt in ("-x", "--exclude"):
            exclude.append(optarg)
        elif opt in ("--p4d",):
            setupOpts["p4d"] = optarg
        elif opt in ("-c", "--clean"):
            justClean = 1
        elif opt in ("-n", "--no-clean"):
            clean = 0

    retval = None
    if not justClean:
        _setUp(**setupOpts)
    try:
        if not justClean:
            retval = test(testModules, testDir=testDir, exclude=exclude)
    finally:
        if clean:
            _tearDown(**setupOpts)
    return retval

if __name__ == '__main__':
    sys.exit(main(sys.argv))

