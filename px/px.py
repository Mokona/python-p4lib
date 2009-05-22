#!/usr/bin/env python
# Copyright (c) 2002-2005 ActiveState Corp.
# See LICENSE.txt for license details.
# Author:
#   Trent Mick (TrentM@ActiveState.com)
# Home:
#   http://trentm.com/projects/px/

"""
    px -- A super-p4

    'px' is a wrapper around the standard 'p4' Perforce client
    application. 'px' replaces, extends, or adds new features to 'p4'.
    In general you should be able to call 'px' just as you would 'p4'.

    Note that this is just recommended for interactive usage. Automated
    usage of the Perforce client should not rely on 'px' being *that*
    reliable. Specifically, output from px does not adhere to p4's '-s'
    option.
"""
pxOptionsDoc = """\
    px Options:
        --help          print this message plus specific 'px' help
        -V, --version   print px and p4 client version
        -g              like -G, except Python objects are unmarshalled and
                        pretty-printed
        --self-test     run px's self test suite and exit

"""

__revision__ = "$Id: px.py 2225 2008-01-23 18:17:55Z trentm $"
__version_info__ = (0, 9, 5)
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import getopt
import pprint
import cmd
import re
import types
import glob
import marshal
import time

import p4lib


#---- exceptions

class PxError(Exception):
    pass


#---- global data

__test__ = {}           # The explicitly mark private methods for doctest.


#---- internal logging facility

class _Logger:
    DEBUG, INFO, WARN, ERROR, CRITICAL = range(5)
    def __init__(self, threshold=None, streamOrFileName=sys.stderr):
        if threshold is None:
            self.threshold = self.WARN
        else:
            self.threshold = threshold
        if type(streamOrFileName) == types.StringType:
            self.stream = open(streamOrFileName, 'w')
            self._opennedStream = 1
        else:
            self.stream = streamOrFileName
            self._opennedStream = 0
    def __del__(self):
        if self._opennedStream:
            self.stream.close()
    def _getLevelName(self, level):
        levelNameMap = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARN: "WARN",
            self.ERROR: "ERROR",
            self.CRITICAL: "CRITICAL",
        }
        return levelNameMap[level]
    def log(self, level, msg):
        if level < self.threshold:
            return
        message = "%s: " % self._getLevelName(level).lower()
        message = message + msg + "\n"
        self.stream.write(message)
        self.stream.flush()
    def debug(self, msg):
        self.log(self.DEBUG, msg)
    def info(self, msg):
        self.log(self.INFO, msg)
    def warn(self, msg):
        self.log(self.WARN, msg)
    def error(self, msg):
        self.log(self.ERROR, msg)
    def fatal(self, msg):
        self.log(self.CRITICAL, msg)

if 1:   # normal
    log = _Logger(_Logger.WARN)
else:   # debugging
    log = _Logger(_Logger.DEBUG)


#---- internal support stuff

def _isdir(dirname):
    r"""os.path.isdir() doesn't work for UNC mount points. Fake it.
    
    # For an existing mount point (want: _isdir() == 1)
    os.path.ismount(r"\\crimper\apps") -> 1
    os.path.exists(r"\\crimper\apps") -> 0
    os.path.isdir(r"\\crimper\apps") -> 0
    os.listdir(r"\\crimper\apps") -> [...contents...]
    # For a non-existant mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\foo") -> 1
    os.path.exists(r"\\crimper\foo") -> 0
    os.path.isdir(r"\\crimper\foo") -> 0
    os.listdir(r"\\crimper\foo") -> WindowsError
    # For an existing dir under a mount point (want: _isdir() == 1)
    os.path.mount(r"\\crimper\apps\Komodo") -> 0
    os.path.exists(r"\\crimper\apps\Komodo") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo") -> 1
    os.listdir(r"\\crimper\apps\Komodo") -> [...contents...]
    # For a non-existant dir/file under a mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\apps\foo") -> 0
    os.path.exists(r"\\crimper\apps\foo") -> 0
    os.path.isdir(r"\\crimper\apps\foo") -> 0
    os.listdir(r"\\crimper\apps\foo") -> []  # as if empty contents
    # For an existing file under a mount point (want: _isdir() == 0)
    os.path.ismount(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.path.exists(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 1
    os.path.isdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> 0
    os.listdir(r"\\crimper\apps\Komodo\latest.komodo-devel.txt") -> WindowsError
    """
    if sys.platform[:3] == 'win' and dirname[:2] == r'\\':
        if os.path.exists(dirname):
            return os.path.isdir(dirname)
        try:
            os.listdir(dirname)
        except WindowsError:
            return 0
        else:
            return os.path.ismount(dirname)
    else:
        return os.path.isdir(dirname)


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if _isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not _isdir(head):
            _mkdir(head)
        if tail:
            log.info('mkdir "%s"' % newdir)
            os.mkdir(newdir)


def _copy(src, dst):
    """works the way a good copy should :)
        - no source, raise an exception
        - destination directory, make a file in that dir named after src
        - source directory, recursively copy the directory to the destination
        - filename wildcarding allowed
    NOTE:
        - This copy CHANGES THE FILE ATTRIBUTES.
    """
    import string, glob, shutil

    assert src != dst, "You are try to copy a file to itself. Bad you! "\
                       "src='%s' dst='%s'" % (src, dst)
    # determine if filename wildcarding is being used
    # (only raise error if non-wildcarded source file does not exist)
    if string.find(src, '*') != -1 or \
       string.find(src, '?') != -1 or \
       string.find(src, '[') != -1:
        usingWildcards = 1
        srcFiles = glob.glob(src)
    else:
        usingWildcards = 0
        srcFiles = [src]

    for srcFile in srcFiles:
        if os.path.isfile(srcFile):
            if usingWildcards:
                srcFileHead, srcFileTail = os.path.split(srcFile)
                srcHead, srcTail = os.path.split(src)
                dstHead, dstTail = os.path.split(dst)
                if dstTail == srcTail:
                    dstFile = os.path.join(dstHead, srcFileTail)
                else:
                    dstFile = os.path.join(dst, srcFileTail)
            else:
                dstFile = dst
            dstFileHead, dstFileTail = os.path.split(dstFile)
            if dstFileHead and not _isdir(dstFileHead):
                _mkdir(dstFileHead)
            if _isdir(dstFile):
                dstFile = os.path.join(dstFile, os.path.basename(srcFile))
            #print "copy %s %s" % (srcFile, dstFile)
            if os.path.isfile(dstFile):
                # make sure 'dstFile' is writeable
                os.chmod(dstFile, 0755)
            log.info('copy "%s" "%s"' % (srcFile, dstFile))
            shutil.copy(srcFile, dstFile)
            # make the new 'dstFile' writeable
            os.chmod(dstFile, 0755)
        elif _isdir(srcFile):
            srcFiles = os.listdir(srcFile)
            if not os.path.exists(dst):
                _mkdir(dst)
            for f in srcFiles:
                s = os.path.join(srcFile, f)
                d = os.path.join(dst, f)
                try:
                    _copy(s, d)
                except (IOError, os.error), why:
                    raise OSError("Can't copy %s to %s: %s"\
                          % (repr(s), repr(d), str(why)))
        elif not usingWildcards:
            raise OSError("Source file %s does not exist" % repr(srcFile))


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
__test__['_joinArgv'] = _joinArgv


class _ListCmd(cmd.Cmd):
    """Pass arglists instead of command strings to commands.

    Modify the std Cmd class to pass arg lists instead of command lines.
    This seems more appropriate for integration with sys.argv which handles
    the proper parsing of the command line arguments (particularly handling
    of quoting of args with spaces).
    """
    name = "_ListCmd"
    
    def cmdloop(self, intro=None):
        raise NotImplementedError

    def onecmd(self, argv):
        # Differences from Cmd
        #   - use an argv, rather than a command string
        #   - don't specially handle the '?' redirect to 'help'
        #   - don't allow the '!' shell out
        if not argv:
            return self.emptyline()
        self.lastcmd = argv
        cmdName = argv[0]
        try:
            func = getattr(self, 'do_' + cmdName)
        except AttributeError:
            return self.default(argv)
        try:
            return func(argv)
        except TypeError, ex:
            sys.stderr.write("%s %s: %s\n" % (self.name, cmdName, ex))
            sys.stderr.write("(Try `%s help %s'.)\n" % (self.name, cmdName))
            if 1:   # for debugging
                print
                import traceback
                traceback.print_exception(*sys.exc_info())

    def default(self, args):
        sys.stdout.write("%s: unknown syntax: %s (Try `%s help'.)\n" %\
            (self.name, " ".join(args), self.name))
        sys.stdout.flush()

    def do_help(self, argv):
        Cmd.do_help(self, ' '.join(argv[1:]))

    def emptyline(self):
        # Differences from Cmd
        #   - Don't repeat the last command for an emptyline.
        pass


class _FindError(Exception): pass

def _addOrSkipFiles((files, filesToSkip, dirsToSkip), dirName, filesInDir):
    """Add all files in the current directory to "files" unless should skip.
    os.path.walk() callback used by _findFiles()
    """
    # Handle skipping.
    toDel = []
    for i in range(len(filesInDir)):
        file = os.path.join(dirName, filesInDir[i])
        if os.path.isdir(file):
            for pattern in dirsToSkip:
                if re.match(pattern, os.path.basename(file)):
                    toDel.append(i)
                    break
        elif os.path.isfile(file):
            for pattern in filesToSkip:
                if re.match(pattern, os.path.basename(file)):
                    toDel.append(i)
                    break
    toDel.reverse() # delete list elems backwards for proper indexing
    for i in toDel:
        del filesInDir[i]
    
    # Add remaining files (not dirs).
    for file in filesInDir:
        file = os.path.join(dirName, file)
        if os.path.isdir(file):
            continue
        files.append(file)

def _findFiles(filespec, filesToSkip=[], dirsToSkip=[]):
    """Return a list of local files described by the given filespec.
    
    A 'filespec' may include normal file glob syntax *OR* trailing a
    trailing '...' after a directory separator to indicate everything
    recursively found under that directory. (Note: this syntax is not
    quite as general as Perforce's which allows mixing of glob syntax
    and '...' and allows '...' anywhere.)

    Directories are NOT included in the results (because Perforce
    doesn't talk about directories).

    A list of file and dir regex patterns to explicitly skip can be
    specified. By default no files are skipped.
    """
    if filespec[-3:] == '...':
        # This indicates to recursively process the dir.
        startDir = os.path.dirname(filespec) or os.curdir
        if '*' in filespec or '?' in filespec:
            raise _FindError("Do not support both glob patterns and '...': "\
                             "'%s'" % filespec)
        if os.path.isfile(startDir):
            raise _FindError("Only support '...' on directories: '%s'."\
                             % filespec)
        if not os.path.isdir(startDir):
            raise _FindError("'%s' directory does not exist." % startDir)
        files = []
        os.path.walk(startDir, _addOrSkipFiles,
                     (files, filesToSkip, dirsToSkip))
        return files
    else:
        allFiles = glob.glob(filespec)
        files = []
        for file in allFiles:
            dirName, fileName = os.path.split(file)
            if not dirName:
                dirName = os.curdir
            _addOrSkipFiles((files, filesToSkip, dirsToSkip), dirName,
                            [fileName])
        return files 



#---- public stuff

class PxShell(_ListCmd):
    """
    This 'p4' is being wrapped by 'px'. See 'px -h' for details and try:

        px help px            list 'px' extensions to 'p4'

    Summary of 'px' changes:

        px --help               See 'px help usage'.
        px -V, --version        See 'px help usage'.
        px -g ...               See 'px help usage'.
        px annotate ...         See 'px help annotate'.
        px backout ...          See 'px help backout'.
        px changes -d ...       See 'px help changes'.
        px diff -sn --skip ...  See 'px help diff'.
        px diff -c <change> ... See 'px help diff'.
        px genpatch [<change>]  See 'px help genpatch'.
    """
    name = 'px'
    def __init__(self, optv):
        """Init px wrapper shell with args needed to drive p4.

        'optv' is the canonicalized (i.e. separate -Gs into -G -s) p4/px
            options (i.e. everything between 'px' and a command name).
        """
        self.__p4optv = optv
        # Treat '-g' like '-G' except the marshal'ed Python dicts
        # will be unmarshal'ed.
        if '-g' in self.__p4optv:
            self.__p4optv[self.__p4optv.index('-g')] = '-G'
            self.__unmarshal = 1
        else:
            self.__unmarshal = 0
        # Drop '-s'. 'p4' implements this on the client side and so
        # should 'px' (XXX though it does not yet), so the option should
        # not be passed to the server.
        if '-s' in self.__p4optv:
            self.__p4optv.remove('-s')
            log.warn("dropping '-s' option, px cannot yet handle it")
        _ListCmd.__init__(self)

    def _p4run(self, argv):
        """Run 'p4' with the given arguments and using px extensions.

        "argv" is a list of command line args *after* the p4 option vector.
        """
        log.debug("PxShell._p4run(%s) # self.__p4optv=%s"\
                  % (argv, self.__p4optv))
        p4argv = ['p4'] + self.__p4optv + argv
        cmd = _joinArgv(p4argv)
        if self.__unmarshal:
            if sys.platform.startswith('win'):
                i, o, e = os.popen3(cmd)
            else:
                import popen2
                p = popen2.Popen3(cmd, 1)
                i, o, e = p.tochild, p.fromchild, p.childerr
            error = e.read()
            if error:
                sys.stderr.write(error)
            else:
                try:
                    while 1:
                        packet = marshal.load(o)
                        pprint.pprint(packet)
                except EOFError:
                    pass
            i.close()
            e.close()
            if sys.platform.startswith('win'):
                retval = o.close()
            else:
                pid, rv = os.wait()
                if os.WIFEXITED(rv):
                    retval = os.WEXITSTATUS(rv)
                else:
                    raise PxError("'%s' did not exit properly: %d"\
                                  % (cmd, rv))
            return retval
        else:
            retval = os.system(cmd)
            if not sys.platform.startswith('win'):
                if os.WIFEXITED(retval):
                    retval = os.WEXITSTATUS(retval)
                else:
                    raise PxError("'%s' did not exit properly: %d"\
                                  % (cmd, retval))
            return retval

    def _p4pcapture(self, argv):
        """Return popen results from spawning 'p4' with the given
        arguments and using px extensions. Raise PxError if there is an
        error running the commands.

        "argv" is a list of command line args *after* the p4 option vector.
        """
        log.debug("PxShell._p4pcapture(%s) # self.__p4optv=%s"\
                  % (argv, self.__p4optv))
        p4argv = ['p4'] + self.__p4optv + argv
        cmd = _joinArgv(p4argv)
        if sys.platform.startswith('win'):
            i, o, e = os.popen3(cmd)
        else:
            import popen2
            p = popen2.Popen3(cmd, 1)
            i, o, e = p.tochild, p.fromchild, p.childerr
        output = o.readlines()
        error = e.readlines()
        i.close()
        e.close()
        if sys.platform.startswith('win'):
            retval = o.close()
        else:
            pid, rv = os.wait()
            if os.WIFEXITED(rv):
                retval = os.WEXITSTATUS(rv)
            else:
                raise PxError("'%s' did not exit properly: %d"\
                              % (cmd, rv))
        return output, error, retval

    def default(self, argv):
        return self._p4run(argv)

    def emptyline(self):
        self.do_help(['help'])

    def _do_one_help(self, arg):
        try:
            # If help_<arg1>() exists, then call it.
            func = getattr(self, 'help_' + arg)
        except AttributeError:
            # Else call the Perforce equivalent (if it has such a
            # command) and print do_<arg1>()'s doc string (if it has
            # one) after.
            dummy, dummy, p4HasNoHelp = self._p4pcapture(['help', arg])
            try:
                doc = getattr(self, 'do_' + arg).__doc__
            except AttributeError:
                doc = None
            if not p4HasNoHelp: # p4 *does* have help, print it
                retval = self._p4run(['help', arg])
            if doc: # *do* have px help, print that
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
                retval = None
            elif p4HasNoHelp:
                # no p4 *or* px help, run 'p4 help <arg>' for std err
                retval = self._p4run(['help', arg])
            return retval
        else:
            return func()

    def do_help(self, argv):
        if argv[1:]:
            for arg in argv[1:]:
                retval = self._do_one_help(arg)
                if retval:
                    return retval
        else:
            # If bare 'help' is called, call the Perforce equivalent and
            # print this class's doc string (if it has one) after.
            retval = self._p4run(argv)
            doc = self.__class__.__doc__
            if doc:
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
            return retval

    def help_commands(self):
        retval = self._p4run(['help', 'commands'])
        sys.stdout.write("""\
    Additional 'px' commands:

        annotate   Identify last change to each line in given file
        backout    Backout the given submitted change number.
        genpatch   Generate patches for pending or submitted changelists.

    Extended 'px' commands:

        changes    Add 'px changes -d' option to print change diffs.
        diff       Add 'px diff -sn' option to list new local files.

""")
        sys.stdout.flush()
        return retval

    def help_usage(self):
        retval = self._p4run(['help', 'usage'])
        sys.stdout.write(pxOptionsDoc)
        sys.stdout.flush()
        return retval

    def help_px(self):
        sys.stdout.write("""\

    'px' entensions to 'p4':

    px --help
        Add px-specific help output to the usual 'p4 -h' and 'p4 -?'.
        See 'px help usage'.

    px -V, --version
        Print px-specific version information in addition to the usage
        'p4 -V' output.  See 'px help usage'.

    px -g ...
        Format input/output as *un*marshalled Python objects. Compare to
        the usual 'p4 -G ...'.  See 'px help usage'.

    px annotate ...
        Identify last change to each line in given file, like 'cvs
        annotate' or 'p4pr.pl'.  See 'px help annotate'.

    px backout ...
        Provide all the general steps for rolling back a perforce
        change as described in Perforce technote 14.  See 'px help
        backout'.

    px changes -d ...
        Print the full 'p4 describe -du' output for each listed change.
        See 'px help changes'.

    px diff -sn --skip ...
        List local files not in the p4 depot. Useful for importing new
        files into a depot via 'px diff -sn --skip ./... | px -x - add'.
        See 'px help diff'.

    px diff -c <change> ...
        Limit diffing to files opened in the given pending change.  See
        'px help diff'.

    px genpatch [<change>]
        Generate a patch (usable by the GNU 'patch' program) from a
        pending or submitted chagelist.  See 'px help genpatch'.
""")
        sys.stdout.flush()

    def do_annotate(self, argv):
        """
    annotate -- Identify last change to each line in given file

    px annotate [ -i ] <file>

        Like 'cvs annotate' (and 'p4pr.pl') this will markup each line
        in the given file with information on where the last change to
        that line originated (which user submitted that change, the
        change number, the file revision). A specific file revision may
        be specified via #... and @... notation.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], 'i')
        except getopt.GetoptError, ex:
            sys.stderr.write("px annotate: error: %s\n" % ex)
            sys.stderr.write("Try 'px help annotate'.\n")
            return 1
        followBranches = 0
        for opt, optarg in optlist:
            if opt == '-i':
                followBranches = 1
                raise NotImplementedError("-i not supported yet")
        
        if len(args) != 1:
            sys.stderr.write("px annotate: error: incorrect number of args\n")
            sys.stderr.write("Try 'px help annotate'.\n")
            return 1
        else:
            change = re.search('(.*)(@\d+)', args[0])
            revision = re.search('(.*)(#\d+)', args[0])
            if change:
                file, suff = change.groups()
            elif revision:
                file, suff = revision.groups()
            else:
                file, suff = args[0], ''
            
        # Prepare an argv for making 'p4 ...' calls with the same args.
        # Drop -s because its output differences can screwup matching
        # done below.
        p4argv = ['p4'] + self.__p4optv
        while '-s' in p4argv:
            p4argv.remove('-s')

        # Check that the file specification maps to exactly one file.
        p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )
        files = p4.files(file+suff)
        if not files:
            sys.stderr.write("px annotate: error: '%s' - no such file\n"\
                             % file+suff)
            return 1
        elif len(files) > 1: 
            sys.stderr.write("px annotate: error: '%s' maps to more than "\
                             "one file\n" % file+suff)
            return 1
            
        # Check that the revision is not deleted.
        if files[0]['action'] == 'delete':
            sys.stderr.write("px annotate: error: '%s#%s' is deleted\n"\
                             % (files[0]['depotFile'], files[0]['rev']))
            return 1
        
        # Get the fullname of the file and the history.
        filelog = p4.filelog(file+suff)[0]
        log.debug("depotFile: %s" % filelog['depotFile'])

        # Ensure that the file has never been binary.
        #XXX Perhaps should not punt on this. If the most recent version
        #    is text then should be able to handle it.
        for rev in filelog['revs']:
            if rev['type'].find('binary') != -1:
                sys.stderr.write("px annotate: error: '%s#%s' is of "\
                                 "type '%s'\n" % (filelog['depotFile'],
                                                  rev['rev'], rev['type']))
                return 1

        # Extract the revision -> change number and revision -> user
        # mappings (where the "author" of a merge/copy/branch is the
        # branch name).
        rev2change = {}
        rev2user = {}
        branchFromRe = re.compile('^(?P<action>copy|branch|merge) '\
                                  'from (?P<from>\/\/.*)#(?P<rev>\d+)$')
        for rev in filelog['revs']:
            revnum = rev['rev']
            rev2change[revnum] = rev['change']
            for note in rev['notes']:
                match = branchFromRe.match(note)
                if match:
                    from_ = match.group('from')
                    for f, n in zip(from_.split('/'),
                                    filelog['depotFile'].split('/')):
                        if f != n:
                            rev2user[revnum] = f
                            break
            if not rev2user.has_key(revnum):
                rev2user[revnum] = rev['user']

        # We are going to start at the base revision (all lines are from
        # that base) and work through each patch, updating the line
        # revisions as we go.
        revs = filelog['revs']
        revs.sort(lambda a,b: cmp(a['rev'], b['rev']))
        file_1 = p4.print_( '%s#%s' % (file, str(revs[0]['rev'])) )[0]
        lines_1 = file_1['text'].split('\n')
        linedata = [{'rev':revs[0]['rev']} for i in lines_1]

        # Properly handle the diff chunk headers (e.g. 10,11c10,13 and
        # 37c39,87) for each revision change. We are just concerned with
        # line numbers here, not that actual text.
        headerRe = re.compile('^(\d+),?(\d*)([acd])(\d+),?(\d*)')
        for rev in revs[1:]:
            revnum = rev['rev']
            diff = p4.diff2(file+'#'+str(revnum-1), file+'#'+str(revnum))
            if not diff.has_key('text'):
                continue
            difflines = diff['text'].split('\n')
            # Apply the diffs in reverse order to maintain correctness
            # of line numbers for each range as we apply it.
            difflines.reverse()
            for line in difflines:
                match = headerRe.search(line)
                if match:
                    la, lb, op, ra, rb = match.groups()
                    if not lb: lb = la
                    if not rb: rb = ra
                    la=int(la); lb=int(lb); ra=int(ra); rb=int(rb)
                    if op == 'a': la += 1
                    if op == 'd': ra += 1
                    linedata[la-1:lb] = [{'rev':revnum} for i in range(rb-ra+1)]

        # Get the text of the selected revision and fill in other data.
        file_head = p4.print_(file+suff)[0]
        text = file_head['text'].split('\n')
        if len(linedata) != len(text):
            raise PxError("internal error applying diffs to '%s'" % file)
        for i in range(len(linedata)):
            linedata[i]['text'] = text[i]
            revnum = linedata[i]['rev']
            linedata[i]['change'] = rev2change[revnum]
            linedata[i]['user'] = rev2user[revnum]

        # Print the data. Note that the interpolated information at the
        # beginning of the line is a multiple of 8 bytes (currently 24)
        # so that the default tabbing of 8 characters works correctly.
        for user in rev2user.values():
            if len(user) > 14:
                fmt = '%5s %23s %6s %4s %s\n'
                break
        else:
            fmt = '%5s %15s %6s %4s %s\n'
        fields = ('line', 'author/branch', 'change', 'rev',
                  '%(depotFile)s#%(rev)s - %(action)s change %(change)s '\
                  '(%(type)s)\n' % file_head)
        sys.stdout.write(fmt % fields)
        sys.stdout.write(fmt % tuple(['-'*len(field) for field in fields]))
        for i in range(len(linedata)):
            line = linedata[i]
            sys.stdout.write(fmt % (i+1, line['user'], line['change'],
                                    line['rev'], line['text']))
        sys.stdout.flush()

    def do_changes(self, argv):
        """\
    px additional options:
        -d      Print the full 'p4 describe -du' output for each change.
                This overrides the -l option.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], 'ilm:s:d')
        except getopt.GetoptError, ex:
            sys.stderr.write("px changes: error: %s\n" % ex)
            sys.stderr.write("Try 'px help changes'.\n")
            return 1
        followIntegrations = 0
        longOutput = 0
        max = None
        status = None
        describe = 0
        for opt, optarg in optlist:
            if opt == '-i':
                followIntegrations = 1
            elif opt == '-l':
                longOutput = 1
            elif opt == '-m':
                max = int(optarg)
            elif opt == '-s':
                status = optarg
            elif opt == '-d':
                describe = 1

        if describe:
            # Get a list of change numbers to describe.
            p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )
            changes = p4.changes(args, followIntegrations=followIntegrations,
                                 longOutput=longOutput, max=max,
                                 status=status)
            changeNums = [c['change'] for c in changes]
            log.info("Changenums to describe: %s" % changeNums)

            # Describe each change.
            for num in changeNums:
                retval = self._p4run(['describe', '-du', str(num)])
                if retval:
                    raise PxError("Error running '%s': retval=%s"\
                                  % (cmd, retval))
        else:
            return self._p4run(argv)

    def do_diff(self, argv):
        """\
    new px options:   [-sn -c changelist#]

        Px adds another -s<flag> option:
                -sn     Local files not in the p4 client.
        
        Px also adds the --skip option (which only makes sense together
        with -sn) to specify that regularly skipped file (CVS control
        files, *~) should be skipped.

        The '-c' option can be used to limit diff'ing to files in the
        given changelist. '-c' cannot be used with any of the '-s' options.
        """
        #TODO:
        #   - A better algorithm. 'px diff -sn' can take a REALLY long
        #     time because it lists every file under the client root
        #     (even if the number of depot files in the client view is
        #     small). A better way to do this would to do the 'p4 have'
        #     first and then spit out each found local file that is not
        #     in that list as they are found. This would show a stream
        #     of results rather than a long delay and then all the
        #     results. Memory consumption could be much reduced. This
        #     would require adding a call back handler to _findFiles.
        #   - Eventually move to my findlib if I get that done.

        # Process options.
        try:
            optlist, files = getopt.getopt(argv[1:], 'd:fs:tc:', ['skip'])
        except getopt.GetoptError, ex:
            sys.stderr.write("px diff: error: %s\n" % ex)
            sys.stderr.write("Try 'px help diff'.\n")
            return 1
        listNewFiles = 0
        haveSeenSOpt = 0
        skip = 0
        change = None
        safeOptv = []
        for opt, optarg in optlist:
            # Note that if multiple -s<flag> options are passed to 'p4
            # diff' it ignores all but the first one. Do not change this
            # behavior.
            if opt == '-s' and optarg.startswith('n'):
                if not haveSeenSOpt:
                    listNewFiles = 1
                haveSeenSOpt = 1
            elif opt == '--skip':
                skip = 1
            elif opt == '-c':
                change = optarg
                try:
                    change = int(change)
                except ValueError:
                    if change != 'default':
                        sys.stderr.write("Invalid changelist number '%s'.\n"\
                                         % change)
                        return 1
            else:
                safeOptv.append(opt)
                if optarg:
                    safeOptv.append(optarg)
                if opt == '-s':
                    haveSeenSOpt = 1

        # Validate the option combinations.
        if skip and not listNewFiles:
            sys.stderr.write("px diff: error: '--skip' only makes sense "\
                             "with '-sn'\n")
            return 1
        if change is not None and haveSeenSOpt:
            sys.stderr.write("px diff: error: cannot use '-c' with "\
                             "'-s<flag>' options\n")
            return 1

        # Perform the chosen action.
        if listNewFiles:
            log.debug("list new files (skip=%d) under %s" % (skip, files))
            p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )

            # Determine the local file specs in the given client view to
            # consider.
            where = p4.where(files or '//...') # default to whole client view
            localfilespecs = [f['localFile'] for f in where if not f['minus']]
            log.debug("list new files (skip=%d) under these local files %s"\
                      % (skip, localfilespecs))
            if skip:
                filesToSkip = ['\.cvsignore', '.*~']
                dirsToSkip = ['CVS']
            else:
                filesToSkip = []
                dirsToSkip = []
            localfiles = []
            for lfs in localfilespecs:
                try:
                    localfiles += _findFiles(lfs, filesToSkip, dirsToSkip)
                except _FindError, ex:
                    log.info(ex)  # Ignore 'dir does not exist' errors.
            log.debug("local files: %s" % pprint.pformat(localfiles))

            p4files = [f['localFile'] for f in p4.have(files)]
            log.debug("p4 files: %s" % pprint.pformat(p4files))

            # Pull out the new files.
            p4filemap = {}
            for f in p4files:
                p4filemap[f] = 1
            newFiles = []
            for f in localfiles:
                if not p4filemap.has_key(f):
                    newFiles.append(f)

            for f in newFiles:
                sys.stdout.write(f + '\n')
                sys.stdout.flush()
        else:
            if change is not None:
                p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )
                if change != "default":
                    try:
                        ch = p4.change(change=change)
                    except p4lib.P4LibError:
                        sys.stderr.write("Change %s unknown." % change)
                        return 1
                    if ch['status'] == 'submitted':
                        sys.stderr.write("Change %d is already commited."\
                                         % change)
                        return 1
                # Filter on files in the given changelist.
                files = [f['depotFile']\
                         for f in p4.opened(files, change=change)]
                argv = argv[:1] + safeOptv + files

            return self._p4run(argv)

    def do_backout(self, argv):
        """
    backout -- backout a specific change number in perforce

    px backout <changelist#>

        Provide all the general steps for rolling back a perforce change.
        c.f. http://www.perforce.com/perforce/technotes/note014.html

        Limitations:
            - Cannot handle changes that include filenames with spaces.
        """
        #TODO:
        #   - '-i' option for interactive mode?
        if len(argv[1:]) != 1:
            sys.stderr.write("Usage: backout <changelist#>\n")
            sys.stderr.write("Missing/wrong number of arguments.\n")
            return 1
        try:
            cnum = int(argv[1])
        except ValueError, ex:
            sys.stderr.write("Invalid changelist number '%s'.\n" % argv[1])
            return 1

        # Get the change description.
        p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )
        desc = p4.describe(cnum, shortForm=1)
        #pprint.pprint(desc)

        # Abort if any of the files is question are currently opened.
        allFiles = [f['depotFile'] for f in desc['files']]
        openedFiles = [f['depotFile'] for f in p4.opened(allFiles)]
        if openedFiles:
            err = "The following files that are part of change %d are "\
                  "currently open. Aborting. %s" % (cnum, openedFiles)
            raise PxError(err)
        #pprint.pprint(allFiles)

        # Abort if don't understand some of the actions.
        actions = [f['action'] for f in desc['files']]
        for action in actions:
            if action not in ("add", "branch", "edit", "integrate",
                              "delete"):
                err = "Don't know how to backout a change with actions "\
                      "other than 'add', 'branch', 'edit', 'integrate', "\
                      "or 'delete': %s\n" % pprint.pformat(desc['files'])
                raise PxError(err)
        #pprint.pprint(actions)

        # Cannot handle spaces in p4 filenames because some popen bug
        # disallows multiple quoted things on one line (or something like
        # that). Assert this.
        #XXX Fix this.
        filesWithSpaces = [f['depotFile'] for f in desc['files']\
                           if ' ' in f['depotFile']]
        if filesWithSpaces:
            raise PxError("The following files in this change have "\
                          "spaces. This implementation cannot handle"\
                          "that: %s" % filesWithSpaces)

        #---- example steps for backing out this change
        # Change 1000 by trudi@spice on 1999/07/27 11:47:04
        # 
        #         Revamp web pages.
        # 
        # Affected files ...
        # 
        # ... //depot/foo#1 add
        # ... //depot/bar#3 delete
        # ... //depot/ola#4 edit
        #
        # Treat "integrate" as equivalent to "edit".
        # Treat "branch" as equivalent to "add".
        #
        # (1) p4 sync @999
        log.info("(1/9) Sync to the change before (%d).\n" % (cnum-1))
        prevFiles = ['%s@%d' % (f['depotFile'], cnum-1)\
                     for f in desc['files']\
                     if f['action'] in ('delete', 'edit', 'integrate')]
        if prevFiles:
            p4.sync(prevFiles)

        # (2) p4 edit //depot/ola
        log.info("(2/9) Open editted files for edit.\n")
        editFiles = [f['depotFile'] for f in desc['files']\
                     if f['action'] in ('edit', 'integrate')]
        if editFiles:
            p4.edit(editFiles)

        # (3) p4 add //depot/bar
        log.info("(3/9) Open deleted files for add.\n")
        delFiles = [f['depotFile'] for f in desc['files']\
                    if f['action'] == 'delete']
        if delFiles:
            p4.add(delFiles)

        # (4) p4 sync @1000
        log.info("(4/9) Sync to the change to back out.\n")
        currFiles = ['%s@%d' % (f['depotFile'], cnum)\
                     for f in desc['files']]
        p4.sync(currFiles)

        # (5) p4 resolve -ay 
        log.info("(5/9) 'Resolve'-away the unwanted changes.\n")
        #XXX should only resolve if necessary (c.f. p4 resolve -n?),
        #    really???
        p4.resolve(allFiles, autoMode='y')

        # (6) p4 sync
        log.info("(6/9) Sync to the latest depot revision.\n")
        p4.sync(allFiles)

        # (7) p4 resolve
        log.info("(7/9) Resolve any conflicts with the latest depot revision.\n")
        # Try to automatically resolve first...
        p4.resolve(allFiles)
        # ...then manually resolve those that need it.
        #XXX Should this ever be needed? How about if guarantee that
        #    files in question have not been opened.
        conflictFiles = [f['depotFile']\
                         for f in p4.resolve(allFiles, dryrun=1)]
        if conflictFiles:
            err = "The following files still need to be manually resolved. "\
                  "Aborting with opened files. %s" % conflictFiles
            raise PxError(err)

        # (8) p4 delete //depot/foo
        log.info("(8/9) Open added files for deletion.\n")
        addFiles = [f['depotFile'] for f in desc['files']\
                    if f['action'] in ('add', 'branch')]
        if addFiles:
            p4.delete(addFiles)

        # (9) p4 submit (setup a pending change for this)
        log.info("(9/9) Setup a pending change to submit.\n")
        c = p4.change(allFiles, "Backout change #%d" % cnum)
        sys.stdout.write("Change %d created to backout change %d.\n"\
                         % (c['change'], cnum))
        sys.stdout.write("Submit with 'px submit -c %d'.\n" % c['change'])
        sys.stdout.flush()

    def do_genpatch(self, argv):
        """
    genpatch -- generate a patch from a pending or submitted changelist

    px genpatch [<changelist#>]

        Generate a patch (i.e. can later be used as input for the
        'patch' program) for a given changelist number. If no change
        number is given then a patch for the 'default' changelist is
        generated. The patch is printed on stdout.

        Files opened for 'add', 'delete' or 'branch' are inlined such
        that application with 'patch' will create or delete the intended
        files.
        """
        #TODO:
        #   - Would an optional [<files> ...] argument be useful or is
        #     that overkill? E.g. 'p4 genpatch ./...' (I think that that
        #     would be very useful.
        #   - Could add '-f' option to only warn on 'out of sync'.
        #   - Could add '-d<flag>' option to control to diff format.
        #     Context and unified allowed.
        #   - Handling binary files that cannot be diff'd
        #   - Option to be able to control the base dir so the patch -p#
        #     number can be controlled. Dunno what form that should
        #     take.

        # Process options.
        diffFormat = 'u'
        if diffFormat == 'u':
            prefixes = ('---', '+++')
        elif diffFormat == 'c':
            prefixes = ('***', '---')

        # Process args.
        if not argv[1:]:
            change = 'default'
        elif len(argv[1:]) == 1:
            change = argv[1]
            try:
                change = int(change)
            except ValueError:  
                # Stupidly, p4win's new Tool %c interpolation will use
                # "Default", on which the normal p4.exe client will die.
                change = change.lower()
                if change != 'default':
                    sys.stderr.write("Invalid changelist number '%s'.\n"\
                                     % change)
                    return 1
        else:
            sys.stderr.write("Usage: genpatch [<changelist#>]\n")
            sys.stderr.write("Missing/wrong number of arguments.\n")
            return 1

        # Validate the given change number.
        p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )
        submitted = [c['change'] for c in p4.changes(status='submitted')]
        pending = [c['change'] for c in p4.changes(status='pending')]
        if change in submitted:
            status = 'submitted'
        elif change in pending+['default']:
            status = 'pending'
        else:
            sys.stderr.write("Change %s unknown." % change)
            return 1

        # Get list of files to include in patch.
        if status == 'submitted':
            d = p4.describe(change, diffFormat='u')
            desc = d['description']
            files = d['files']
            diffs = d['diff']
        elif status == 'pending':
            files = p4.opened(change=change)
            if change == 'default':
                desc = None
            else:
                desc = p4.change(change=change)['description']
            if files:
                diffs = p4.diff([f['depotFile'] for f in files],
                                diffFormat='u')
            else:
                diffs = []

        # Make a single string from 'diffs' with appropriate delimiters
        # for the "patch" program.
        diffstr = ''
        timestamp = time.asctime()
        for diff in diffs:
            # Perforce std header, e.g.:
            #   ==== //depot/apps/px/ReadMe.txt#5 (text) ====
            # or
            #   ==== //depot/foo.doc#42 - c:\trentm\foo.doc ==== (binary)
            if diff.has_key('localFile'):
                diffstr += "==== %(depotFile)s#%(rev)s - %(localFile)s ===="\
                           % diff
                if diff['binary']:
                    diffstr += " (binary)"
                diffstr += "\n"
            else:
                diffstr += "==== %(depotFile)s#%(rev)s (%(type)s) ====\n"\
                           % diff
            # Patch header, e.g. for unified diffs:
            #   Index: apps/px/test/ToDo.txt
            #   --- apps/px/test/ToDo.txt.~1~   Fri May 31 21:17:17 2002
            #   +++ apps/px/test/ToDo.txt       Fri May 31 21:17:17 2002
            # or for context diffs:
            #   Index: apps/px/test/ToDo.txt
            #   *** apps/px/test/ToDo.txt.~1~   Fri May 31 21:26:47 2002
            #   --- apps/px/test/ToDo.txt       Fri May 31 21:26:47 2002
            fname = diff['depotFile'][len('//depot/'):]

            if diff.has_key('text'):
                diffstr += "Index: %s\n" % fname
                diffstr += "%s %s.~1~\t%s\n" % (prefixes[0], fname, timestamp)
                diffstr += "%s %s\t%s\n" % (prefixes[1], fname, timestamp)
                # The diff text.
                diffstr += ''.join(diff['text'])
                if diffstr[-1] != '\n':
                    diffstr += "\n\\ No newline at end of file\n"

        # Inline added files into the diff.
        addedfiles = [f for f in files if f['action'] in ('add', 'branch')]
        for f in addedfiles:
            # May have to get file type from 'p4 files'.
            if status == 'submitted':
                f['type'] = p4.files(f['depotFile'])[0]['type']
            # Skip file if it is binary.
            if f['type'].startswith('binary'):
                log.warn("Cannot inline '%s' because it is binary."\
                         % f['depotFile'])
                continue
            # Get the file contents.
            if status == "pending":
                # Read the file contents from disk.
                localFile = p4.where(f['depotFile'])[0]['localFile']
                if not os.path.exists(localFile):
                    continue
                lines = open(localFile, 'r').readlines()
            else:
                # Get the file contents via 'p4 print'.
                fnameRev = "%s#%s" % (f['depotFile'], f['rev'])
                lines = p4.print_(fnameRev)[0]['text'].split('\n')
                if not lines[-1]: lines = lines[:-1] # drop empty last line
                lines = [line+'\n' for line in lines]
            # Inline the file.
            diffstr += "\n==== %(depotFile)s#%(rev)s (%(type)s) ====\n" % f
            if len(lines) < 2:
                ln = ""
            else:
                ln = "," + str(len(lines))
            fname = f['depotFile'][len('//depot/'):]
            diffstr += "Index: %s\n" % fname
            diffstr += "%s %s.~1~\t%s\n" % (prefixes[0], fname, timestamp)
            diffstr += "%s %s\t%s\n" % (prefixes[1], fname, timestamp)
            diffstr += "@@ -0,0 +1%s @@\n" % ln
            diffstr += '+' + '+'.join(lines)
            if diffstr[-1] != '\n':
                diffstr += "\n\\ No newline at end of file\n"
                
        if diffstr: # std patch terminator
            diffstr += "End of Patch."

        patch = p4lib.makeForm(description=desc, files=files,
                               differences=diffstr)
        if patch: # ViM-specific hack to have it colorize patches as diffs.
            patch = "diff\n" + patch

        sys.stdout.write(patch)


def px(argv):
    optlist, args = getopt.getopt(argv[1:], 'h?Vc:d:H:p:P:u:x:Gsg',
        ['help', 'version', 'self-test'])
    optv = []   # Canonicalized 'px' option vector.
    for opt, optarg in optlist:
        # Terminal options:
        if opt in ('--self-test',):
            _test()
            return
        if opt in ('-?', '-h', '--help'):
            sys.stdout.write(__doc__ + '\n')
            sys.stdout.write("    ")  # Tweak the 'p4 -h' lead indentation.
            sys.stdout.flush()
            retval = os.system('p4 -h')
            sys.stdout.write(pxOptionsDoc)
            sys.stdout.flush()
            return retval
        if opt in ('--version', '-V'):
            sys.stdout.write("px %s\n" % __version__)
            sys.stdout.flush()
            while '--version' in argv:
                argv[argv.index('--version')] = '-V'
            p4argv = argv
            p4argv[0] = 'p4'
            retval = os.system('p4 -V')
            return retval
        # Non-terminal options:
        optv.append(opt)
        if optarg:
            optv.append(optarg)

    shell = PxShell(optv)
    return shell.onecmd(args)


#---- mainline

def _test():
    # To run from the command line: px --self-test
    # (px.py must be on sys.path. This requires Python >=2.1 to run.)
    print "Running px's self test."
    sys.argv.append('-v')
    import doctest, px
    return doctest.testmod(px)

if __name__ == "__main__":
    sys.exit( px(sys.argv) )

