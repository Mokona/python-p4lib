#!/usr/bin/env python
# Copyright (c) 2004-2006 ActiveState Software Inc.
# Written by: Trent Mick (TrentM@ActiveState.com)
# License: MIT License (http://www.opensource.org/licenses/mit-license.php)
# Homepage: http://trentm.com/projects/px/

"""
    An OO interface to 'p4' (the Perforce client command line app).

    Usage:
        import p4lib
        p4 = p4lib.P4(<p4options>)
        result = p4.<command>(<options>)

    For more information see the doc string on each command. For example:
        print p4lib.P4.opened.__doc__
    
    Implemented commands:
        add (limited test suite), branch, branches, change, changes (no
        test suite), client, clients, delete, describe (no test suite),
        diff, edit (no test suite), files (no test suite), filelog (no
        test suite), flush, have (no test suite), label, labels, opened,
        print (as print_, no test suite), resolve, revert (no test
        suite), submit, sync, where (no test suite), fstat (no test suite)
    Partially implemented commands:
        diff2
    Unimplemented commands:
        admin, counter, counters, depot, depots, dirs, fix, fixes,
        group, groups, help (no point), integrate, integrated,
        job, jobs, jobspec, labelsync, lock, obliterate, passwd,
        protect, rename (no point), reopen, resolved, review, reviews,
        set, triggers, typemap, unlock, user, users, verify

    XXX Describe usage of parseForm() and makeForm().
"""
#TODO:
#   - There is much similarity in some commands, e.g. clients, changes,
#     branches in one group; client, change, branch, label in another.
#     Should share implementation between these all.

__version_info__ = (0, 9, 6, 'beta')
__version__ = '.'.join(map(str, __version_info__))

import os
import sys
import pprint
import re
import marshal
import getopt
import tempfile
import copy

#---- exceptions


class P4LibError(Exception):
    pass


#---- internal logging facility


class _Logger:
    DEBUG, INFO, WARN, ERROR, CRITICAL = range(5)

    def __init__(self, threshold=None, streamOrFileName=sys.stderr):
        if threshold is None:
            self.threshold = self.WARN
        else:
            self.threshold = threshold
        if isinstance(streamOrFileName, str):
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

    def log(self, level, msg, *args):
        if level < self.threshold:
            return
        message = "%s: " % self._getLevelName(level).lower()
        message = message + (msg % args) + "\n"
        self.stream.write(message)
        self.stream.flush()

    def debug(self, msg, *args):
        self.log(self.DEBUG, msg, *args)

    def info(self, msg, *args):
        self.log(self.INFO, msg, *args)

    def warn(self, msg, *args):
        self.log(self.WARN, msg, *args)

    def error(self, msg, *args):
        self.log(self.ERROR, msg, *args)

    def fatal(self, msg, *args):
        self.log(self.CRITICAL, msg, *args)

if 1:   # normal
    log = _Logger(_Logger.WARN)
else:   # debugging
    log = _Logger(_Logger.DEBUG)


#---- internal support stuff

def _escapeArg(arg):
    """Escape the given command line argument for the shell."""
    #XXX There is a *lot* more that we should escape here.
    #XXX This is also not right on Linux, just try putting 'p4' is a dir
    #    with spaces.
    return arg.replace('"', r'\"')


def _joinArgv(argv):
    r"""Join an arglist to a string appropriate for running.
        >>> import os
        >>> _joinArgv(['foo', 'bar "baz'])
        'foo "bar \\"baz"'
    """
    cmdstr = ""
    for arg in argv:
        # Quote args with '*' because don't want shell to expand the
        # argument. (XXX Perhaps that should only be done for Windows.)
        if ' ' in arg or '*' in arg:
            cmdstr += '"%s"' % _escapeArg(arg)
        else:
            cmdstr += _escapeArg(arg)
        cmdstr += ' '
    if cmdstr.endswith(' '):
        cmdstr = cmdstr[:-1]  # strip trailing space
    return cmdstr


def _run(argv):
    """Prepare and run the given arg vector, 'argv', and return the
    results.  Returns (<stdout lines>, <stderr lines>, <return value>).
    Note: 'argv' may also just be the command string.
    """
    if isinstance(argv, list) or isinstance(argv, tuple):
        cmd = _joinArgv(argv)
    else:
        cmd = argv
    log.debug("Running '%s'..." % cmd)
    if sys.platform.startswith('win'):
        i, o, e = os.popen3(cmd)
        output = o.read()
        error = e.read()
        i.close()
        e.close()
        retval = o.close()
    else:
        import popen2
        p = popen2.Popen3(cmd, 1)
        i, o, e = p.tochild, p.fromchild, p.childerr
        output = o.read()
        error = e.read()
        i.close()
        o.close()
        e.close()
        rv = p.wait()
        if os.WIFEXITED(rv):
            retval = os.WEXITSTATUS(rv)
        else:
            raise P4LibError("Error running '%s', it did not exit "
                             "properly: rv=%d" % (cmd, rv))
    if retval:
        raise P4LibError("Error running '%s': error='%s' retval='%s'"
                         % (cmd, error, retval))
    log.debug("output='%s'", output)
    log.debug("error='%s'", error)
    log.debug("retval='%s'", retval)
    return output, error, retval


def _specialsLast(a, b, specials):
    """A cmp-like function, sorting in alphabetical order with
    'special's last.
    """
    if a in specials and b in specials:
        return cmp(a, b)
    elif a in specials:
        return 1
    elif b in specials:
        return -1
    else:
        return cmp(a, b)


def _writeTemporaryForm(form):
    formfile = tempfile.mktemp()
    fout = open(formfile, 'w')
    fout.write(form)
    fout.close()

    return formfile


def _removeTemporaryForm(formfile):
    if formfile:
        os.remove(formfile)


def _values_to_int(dictionnary, list_of_keys):
    for key in list_of_keys:
        if key in dictionnary:
            value = dictionnary[key]
            if value:
                try:
                    dictionnary[key] = int(value)
                except ValueError:
                    pass

    return dictionnary


def _prune_none_values(dictionnary):
    for key in dictionnary.keys():
        if dictionnary[key] is None:
            del dictionnary[key]

    return dictionnary


def _argumentGenerator(arguments):
    result = []
    for key, value in arguments.items():
        if isinstance(value, bool):
            if value:
                result.append(key)
        elif isinstance(value, int):
            result.append(key)
            result.append(str(value))
        elif isinstance(value, str):
            if r"%s" in key:
                if value:
                    result.append(key % value)
            elif value:
                result.append(key)
                result.append(value)
    return result


def _normalizeFiles(files):
    if isinstance(files, str):
        return [files]
    return files


def _parseDiffOutput(output):
    if isinstance(output, str):
        outputLines = output.splitlines(True)
    else:
        outputLines = output
    hits = []
    # Example header lines:
    #   - from 'p4 describe':
    #       ==== //depot/apps/px/ReadMe.txt#5 (text) ====
    #       ==== //depot/main/Apps/Komodo-4.2/src/udl/luddite.py#2 (text+kwx) ====
    #   - from 'p4 diff':
    #       ==== //depot/apps/px/p4lib.py#12 - c:\trentm\apps\px\p4lib.py ====
    #       ==== //depot/foo.doc#42 - c:\trentm\foo.doc ==== (binary)
    header1Re = re.compile(r"^==== (?P<depotFile>//.*?)#(?P<rev>\d+) "
                           r"\((?P<type>[\w+]+)\) ====$")
    header2Re = re.compile("^==== (?P<depotFile>//.*?)#(?P<rev>\d+) - "
                           "(?P<localFile>.+?) ===="
                           "(?P<binary> \(binary\))?$")
    header3Re = re.compile(r"^--- (?P<depotFile>//.*?)\s+.*$")
    header4Re = re.compile(r"^\+\+\+ (?P<localFile>//.*?)\s+.*$")

    LINE_DIFFER_TEXT = "(... files differ ...)\n"
    for line in outputLines:
        header1 = header1Re.match(line)
        header2 = header2Re.match(line)
        header3 = header3Re.match(line)
        header4 = header4Re.match(line)
        if header1:
            hit = header1.groupdict()
            hit['rev'] = int(hit['rev'])
            hits.append(hit)
        elif header2:
            hit = header2.groupdict()
            hit['rev'] = int(hit['rev'])
            hit['binary'] = not not hit['binary']  # get boolean value
            hits.append(hit)
        elif header3:
            hit = header3.groupdict()
            hit['rev'] = 0
            hit['binary'] = False
            hits.append(hit)
        elif header4:
            hits[-1].update(header4.groupdict())
        elif 'text' not in hits[-1] and line == LINE_DIFFER_TEXT:
            hits[-1]['notes'] = [line]
        else:
            # This is a diff line.
            if 'text' not in hits[-1]:
                hits[-1]['text'] = ''
                # XXX 'p4 describe' diff text includes a single
                #     blank line after each header line before the
                #     actual diff. Should this be stripped?
            hits[-1]['text'] += line

    return hits


def _match_or_raise(regex, line, command_msg):
    m = regex.match(line)
    if not m:
        raise P4LibError("Internal error: could not parse "
                         "'p4 %s' output line: '%s'" % (command_msg, line))
    return m


def _rstriponce(line):
    if line and line[-1] == '\n':
        line = line[:-1]
    return line

#---- public stuff


def makeForm(**kwargs):
    """Return an appropriate P4 form filled out with the given data.
    
    In general this just means tranforming each keyword and (string)
    value to separate blocks in the form. The section name is the
    capitalized keyword. Single line values go on the same line as
    the section name. Multi-line value succeed the section name,
    prefixed with a tab, except some special section names (e.g.
    'differences'). Text for "special" sections are NOT indented, have a
    blank line after the header, and are placed at the end of the form.
    Sections are separated by a blank line.

    The 'files' key is handled specially. It is expected to be a
    list of dicts of the form:
        {'action': 'add', # 'action' may or may not be there
         'depotFile': '//depot/test_edit_pending_change.txt'}
    As well, the 'change' value may be an int.
    """
    # Do special preprocessing on the data.
    for key, value in kwargs.items():
        if key == 'files':
            strval = ''
            for f in value:
                if 'action' in f:
                    strval += '%(depotFile)s\t# %(action)s\n' % f
                else:
                    strval += '%(depotFile)s\n' % f
            kwargs[key] = strval
        if key == 'change':
            kwargs[key] = str(value)
    
    # Create the form
    form = ''
    specials = ['differences']
    keys = kwargs.keys()
    keys.sort(lambda a, b, s=specials: _specialsLast(a, b, s))

    for key in keys:
        value = kwargs[key]
        if value is None:
            pass
        # If there is multiline input or we are setting the "description"
        # field, ensure the key and the data are newline separated.
        #
        # The description field should *always* contain a newline separator,
        # whilst the perforce server handles a commit without the newline sep,
        # most perforce triggers will reject this style of form description.
        # http://bugs.activestate.com/show_bug.cgi?id=73103
        elif len(value.split('\n')) > 1 or key == "description":
            form += '%s:\n' % key.capitalize()
            if key in specials:
                form += '\n'
            for line in value.split('\n'):
                if key in specials:
                    form += line + '\n'
                else:
                    form += '\t' + line + '\n'
        else:
            form += '%s:\t%s\n' % (key.capitalize(), value)
        form += '\n'
    return form


def parseForm(content):
    """Parse an arbitrary Perforce form and return a dict result.

    The result is a dict with a key for each "section" in the
    form (the key name will be the section name lowercased),
    whose value will, in general, be a string with the following
    exceptions:
        - A "Files" section will translate into a list of dicts
          each with 'depotFile' and 'action' keys.
        - A "Change" value will be converted to an int if
          appropriate.
    """
    def splitSections(lines):
        # Example form:
        #   # A Perforce Change Specification.
        #   #
        #   #  Change:      The change number. 'new' on a n...
        #   <snip>
        #   #               to this changelist.  You may de...
        #   
        #   Change: 1
        #   
        #   Date:   2002/05/08 23:24:54
        #   <snip>
        #   Description:
        #           create the initial change
        #   
        #   Files:
        #           //depot/test_edit_pending_change.txt    # add
        spec = {}

        currkey = None  # If non-None, then we are in a multi-line block.
        for line in lines:
            if line.strip().startswith('#'):
                continue    # skip comment lines
            if currkey:     # i.e. accumulating a multi-line block
                if line.startswith('\t'):
                    spec[currkey] += line[1:]
                elif not line.strip():
                    spec[currkey] += '\n'
                else:
                    # This is the start of a new section. Trim all
                    # trailing newlines from block section, as
                    # Perforce does.
                    spec[currkey] = spec[currkey].rstrip("\n")
                    currkey = None
            if not currkey:  # i.e. not accumulating a multi-line block
                if not line.strip():
                    continue  # skip empty lines
                key, remainder = line.split(':', 1)
                if not remainder.strip():   # this is a multi-line block
                    currkey = key.lower()
                    spec[currkey] = ''
                else:
                    spec[key.lower()] = remainder.strip()
        if currkey:
            # Trim all trailing newlines from block section, as
            # Perforce does.
            spec[currkey] = spec[currkey].rstrip("\n")

        return spec

    def fileToDict(line, fileRe):
        match = fileRe.match(line)
        try:
            return match.groupdict()
        except AttributeError:
            pprint.pprint(line)
            err = "Internal error: could not parse P4 form "\
                  "'Files:' section line: '%s'" % line
            raise P4LibError(err)

    def processSpecialValues(spec):
        for key, value in spec.items():
            if key == "change":
                try:
                    spec[key] = int(value)
                except ValueError:
                    pass
            elif key == "files":
                fileRe = re.compile('^(?P<depotFile>//.+?)\t'
                                    '# (?P<action>\w+)$')
                spec[key] = [fileToDict(line, fileRe)
                             for line in value.split('\n')
                             if line.strip()]

        return spec

    if isinstance(content, str):
        lines = content.splitlines(True)
    else:
        lines = content

    spec = splitSections(lines)
    spec = processSpecialValues(spec)

    return spec


def makeOptv(**options):
    """Create a p4 option vector from the given p4 option dictionary.
    
    "options" is an option dictionary. Valid keys and values are defined by
        what class P4's constructor accepts via P4(**optd).
    
    Example:
        >>> makeOptv(client='swatter', dir='D:\\trentm')
    Returns:
        ['-c', 'client', '-d', 'D:\\trentm']

    Example:
        >>> makeOptv(client='swatter', dir=None)
    Returns:
        ['-c', 'client']
    """
    key_to_option = {"client": "-c",
                     "dir": "-d",
                     "host": "-H",
                     "port": "-p",
                     "password": "-P",
                     "user": "-u"}

    optv = []
    try:
        for key, value in options.items():
            if value:
                optv.append(key_to_option[key])
                optv.append(value)
    except KeyError as key:
        raise P4LibError("Unexpected keyword arg: %s" % key)

    return optv


def parseOptv(optv):
    """Return an option dictionary representing the given p4 option vector.
    
    "optv" is a list of p4 options. See 'p4 help usage' for a list.

    The returned option dictionary is suitable passing to the P4 constructor.

    Example:
        parseP4Optv(['-c', 'swatter', '-d', 'D:\\trentm'])
    Returns:
        {'client': 'swatter', 'dir': 'D:\\trentm'}
    """
    option_to_key = {"-c": "client",
                     "-d": "dir",
                     "-H": "host",
                     "-p": "port",
                     "-P": "password",
                     "-u": "user"}

    optlist, dummy = getopt.getopt(optv, 'hVc:d:H:p:P:u:x:Gs')
    optd = {}
    for opt, optarg in optlist:
        # Some of p4's options are not appropriate for later
        # invocations. For example, '-h' and '-V' override output from
        # running, say, 'p4 opened'; and '-G' and '-s' control the
        # output format which this module is parsing (hence this module
        # should control use of those options).
        if opt in ('-h', '-V', '-x'):
            raise P4LibError("The '%s' p4 option is not appropriate "
                             "for p4lib.P4." % opt)
        elif opt in ('-G', '-s'):
            log.info("Ignoring '%s' option." % opt)
        else:
            key = option_to_key[opt]
            optd[key] = optarg
    return optd


class P4:
    """A proxy to the Perforce client app 'p4'."""
    def __init__(self, p4='p4', **options):
        """Create a 'p4' proxy object.

        "p4" is the Perforce client to execute commands with. Defaults
            to 'p4'.
        Optional keyword arguments:
            "client" specifies the client name, overriding the value of
                $P4CLIENT in the environment and the default (the hostname).
            "dir" specifies the current directory, overriding the value of
                $PWD in the environment and the default (the current
                directory).
            "host" specifies the host name, overriding the value of $P4HOST
                in the environment and the default (the hostname).
            "port" specifies the server's listen address, overriding the
                value of $P4PORT in the environment and the default
                (perforce:1666).
            "password" specifies the password, overriding the value of
                $P4PASSWD in the environment.
            "user" specifies the user name, overriding the value of $P4USER,
                $USER, and $USERNAME in the environment.
        """
        self.p4 = p4
        self.optd = options
        self._optv = makeOptv(**self.optd)

    def _p4run(self, argv, **p4options):
        """Run the given p4 command.
        
        The current instance's p4 and p4 options (optionally overriden by
        **p4options) are used. The 3-tuple (<output>, <error>, <retval>) is
        returned.
        """
        if p4options:
            d = self.optd
            d.update(p4options)
            p4optv = makeOptv(**d)
        else:
            p4optv = self._optv
        argv = [self.p4] + p4optv + argv
        return _run(argv)

    def _run_and_process(self, argv, process_callback,
                         raw, **p4options):
        output, error, retval = self._p4run(argv, **p4options)

        if raw:
            return {'stdout': output, 'stderr': error, 'retval': retval}

        return process_callback(output)

    def _batch_run(self, argv, files, p4options):
        SET_SIZE = 10

        results = {"stdout": '', "stderr": '', "retval": 0}
        if files:
            for i in range(0, len(files), SET_SIZE):
                set_argv = argv[:] + files[i:i + SET_SIZE]
                stdout, stderr, retval = self._p4run(set_argv, **p4options)
                results["stdout"] += stdout
                results["stderr"] += stderr

                #XXX just add up retvals for now?!
                results["retval"] += retval or 0
        else:
            stdout, stderr, retval = self._p4run(argv, **p4options)
            results["stdout"] = stdout
            results["stderr"] = stderr
            results["retval"] = retval

        return results

    def opened(self, files=[], allClients=False, change=None, _raw=False,
               **p4options):
        """Get a list of files opened in a pending changelist.

        "files" is a list of files or file wildcards to check. Defaults
            to the whole client view.
        "allClients" (-a) specifies to list opened files in all clients.
        "change" (-c) is a pending change with which to associate the
            opened file(s).

        Returns a list of dicts, each representing one opened file. The
        dict contains the keys 'depotFile', 'rev', 'action', 'change',
        'type', and, as well, 'user' and 'client' if the -a option
        is used.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Output examples:
        # - normal:
        #   //depot/apps/px/px.py#3 - edit default change (text)
        # - with '-a':
        #   //depot/foo.txt#1 - edit change 12345 (text+w) by trentm@trentm-pliers
        # - none opened:
        #   foo.txt - file(s) not opened on this client.
        optv = _argumentGenerator({'-a': allClients, '-c': change})

        argv = ['opened'] + optv
        results = self._batch_run(argv, _normalizeFiles(files), p4options)
        
        if _raw:
            return results

        lineRe = re.compile('''^
            (?P<depotFile>.*?)\#(?P<rev>\d+)    # //depot/foo.txt#1
            \s-\s(?P<action>\w+)                # - edit
            \s(default\schange|change\s(?P<change>\d+))  # change 12345
            \s\((?P<type>[\w+]+)\)          # (text+w)
            (\sby\s)?                           # by
            ((?P<user>[^\s@]+)@(?P<client>[^\s@]+))?    # trentm@trentm-pliers
            ''', re.VERBOSE)
        files = []
        for line in results["stdout"].splitlines(True):
            match = _match_or_raise(lineRe, line, "opened")
            fileinfo = match.groupdict()
            fileinfo = _values_to_int(fileinfo, ['rev', 'change'])

            if not fileinfo['change']:
                fileinfo['change'] = 'default'

            fileinfo = _prune_none_values(fileinfo)

            files.append(fileinfo)

        return files

    def where(self, files=[], _raw=0, **p4options):
        """Show how filenames map through the client view.

        "files" is a list of files or file wildcards to check. Defaults
            to the whole client view.

        Returns a list of dicts, each representing one element of the
        mapping. Each mapping include a 'depotFile', 'clientFile', and
        'localFile' and a 'minus' boolean (indicating if the entry is an
        Exclusion.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Output examples:
        #  -//depot/foo/Py-2_1/... //trentm-ra/foo/Py-2_1/... c:\trentm\foo\Py-2_1\...
        #  //depot/foo/win/... //trentm-ra/foo/win/... c:\trentm\foo\win\...
        #  //depot/foo/Py Exts.dsw //trentm-ra/foo/Py Exts.dsw c:\trentm\foo\Py Exts.dsw
        #  //depot/foo/%1 //trentm-ra/foo/%1 c:\trentm\foo\%1
        # The last one is surprising. It comes from using '*' in the
        # client spec.
        def where_result_cb(output):
            results = []
            for line in output.splitlines(True):
                # With spaces inside filenames, the parsing is done by
                # searching // and platform specific marker for the
                # third part.
                # Rather dans Regular Expressions.
                fileinfo = {}
                line = _rstriponce(line)
                if line.startswith('-'):
                    fileinfo['minus'] = 1
                    line = line[1:]
                else:
                    fileinfo['minus'] = 0
                depotStart = line.find('//')
                clientStart = line.find('//', depotStart + 2)
                fileinfo['depotFile'] = line[depotStart:clientStart - 1]
                if sys.platform.startswith('win'):
                    assert ':' not in fileinfo['depotFile'],\
                           "Current parsing cannot handle this line '%s'." %\
                           line
                    localStart = line.find(':', clientStart + 2) - 1
                else:
                    assert fileinfo['depotFile'].find(' /') == -1,\
                        "Current parsing cannot handle this line '%s'." % line
                    localStart = line.find(' /', clientStart + 2) + 1
                fileinfo['clientFile'] = line[clientStart:localStart - 1]
                fileinfo['localFile'] = line[localStart:]
                results.append(fileinfo)
            return results

        argv = ['where']
        if files:
            argv += _normalizeFiles(files)

        return self._run_and_process(argv,
                                     where_result_cb,
                                     raw=_raw,
                                     **p4options)

    def have(self, files=[], _raw=0, **p4options):
        """Get list of file revisions last synced.

        "files" is a list of files or file wildcards to check. Defaults
            to the whole client view.
        "options" can be any of p4 option specifiers allowed by .__init__()
            (they override values given in the constructor for just this
            command).

        Returns a list of dicts, each representing one "hit". Each "hit"
        includes 'depotFile', 'rev', and 'localFile' keys.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def have_result_cb(output):
            # Output format is 'depot-file#revision - client-file'
            haveRe = re.compile('(?P<depotFile>.+)#(?P<rev>\d+)'
                                ' - (?P<localFile>.+)')

            all_matches = (_match_or_raise(haveRe, _rstriponce(l), "have")
                           for l in output.splitlines(True))
            hits = [_values_to_int(match.groupdict(), ['rev'])
                    for match in all_matches]

            return hits

        argv = ['have']
        if files:
            argv += _normalizeFiles(files)

        return self._run_and_process(argv,
                                     have_result_cb,
                                     raw=_raw,
                                     **p4options)

    def describe(self, change, diffFormat='', shortForm=False, _raw=False,
                 **p4options):
        """Get a description of the given changelist.

        "change" is the changelist number to describe.
        "diffFormat" (-d<flag>) is a flag to pass to the built-in diff
            routine to control the output format. Valid values are ''
            (plain, default), 'n' (RCS), 'c' (context), 's' (summary),
            'u' (unified).
        "shortForm" (-s) specifies to exclude the diff from the
            description.

        Returns a dict representing the change description. Keys are:
        'change', 'date', 'client', 'user', 'description', 'files', 'diff'
        (the latter is not included iff 'shortForm').

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def describe_result_cb(output):
            desc = {}
            lines = output.splitlines(True)

            changeRe = re.compile('^Change (?P<change>\d+) by (?P<user>[^\s@]+)@'
                                  '(?P<client>[^\s@]+) on (?P<date>[\d/ :]+)$')

            desc = changeRe.match(lines[0]).groupdict()
            desc['change'] = int(desc['change'])

            filesIdx = lines.index("Affected files ...\n")

            desc['description'] = ""
            for line in lines[2:filesIdx - 1]:
                desc['description'] += line[1:].strip()  # drop the leading \t
            if shortForm:
                diffsIdx = len(lines)
            else:
                diffsIdx = lines.index("Differences ...\n")

            fileRe = re.compile('^... (?P<depotFile>.+?)#(?P<rev>\d+) '
                                '(?P<action>\w+)$')

            all_matches = (_match_or_raise(fileRe, l, "describe")
                           for l in lines[filesIdx + 2:diffsIdx - 1])
            desc['files'] = [_values_to_int(match.groupdict(), ['rev'])
                             for match in all_matches]

            if not shortForm:
                desc['diff'] = _parseDiffOutput(lines[diffsIdx + 2:])
            return desc

        if diffFormat not in ('', 'n', 'c', 's', 'u'):
            raise P4LibError("Incorrect diff format flag: '%s'" % diffFormat)

        optv = _argumentGenerator({'-d%s': diffFormat, '-s': shortForm})
        argv = ['describe'] + optv + [str(change)]

        return self._run_and_process(argv,
                                     describe_result_cb,
                                     raw=_raw,
                                     **p4options)

    def change(self, files=None, description=None, change=None, delete=0,
               _raw=0, **p4options):
        """Create, update, delete, or get a changelist description.
        
        Creating a changelist:
            p4.change([<list of opened files>], "change description")
                                    OR
            p4.change(description="change description for all opened files")

        Updating a pending changelist:
            p4.change(description="change description",
                      change=<a pending changelist#>)
                                    OR
            p4.change(files=[<new list of files>],
                      change=<a pending changelist#>)

        Deleting a pending changelist:
            p4.change(change=<a pending changelist#>, delete=1)

        Getting a change description:
            ch = p4.change(change=<a pending or submitted changelist#>)
        
        Returns a dict. When getting a change desc the dict will include
        'change', 'user', 'description', 'status', and possibly 'files'
        keys. For all other actions the dict will include a 'change'
        key, an 'action' key iff the intended action was successful, and
        possibly a 'comment' key.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}

        Limitations: The -s (jobs) and -f (force) flags are not
        supported.
        """
        #XXX .change() API should look more like .client() and .label(),
        #    i.e. passing around a dictionary. Should strings also be
        #    allowed: presumed to be forms?
        def get_change_information(change):
            argv = ['change', '-o', str(change)]

            return self._run_and_process(argv,
                                         lambda output: parseForm(output),
                                         raw=_raw,
                                         **p4options)

        def create_update_delete_parse_result(output):
            lines = output.splitlines(True)
            resultRes = [
                re.compile("^Change (?P<change>\d+)"
                           " (?P<action>created|updated|deleted)\.$"),
                re.compile("^Change (?P<change>\d+) (?P<action>created)"
                           " (?P<comment>.+?)\.$"),
                re.compile("^Change (?P<change>\d+) (?P<action>updated)"
                           ", (?P<comment>.+?)\.$"),
                # e.g., Change 1 has 1 open file(s) associated with it and
                # can't be deleted.
                re.compile("^Change (?P<change>\d+) (?P<comment>.+?)\.$"),
            ]
            for resultRe in resultRes:
                match = resultRe.match(lines[0])
                if match:
                    change = match.groupdict()
                    change = _values_to_int(change, ['change'])
                    break
            else:
                err = "Internal error: could not parse change '%s' "\
                      "output: '%s'" % (action, output)
                raise P4LibError(err)

            return change

        def create_update_execute(form):
            try:
                formfile = _writeTemporaryForm(form)
                argv = ['change', '-i', '<', formfile]

                return self._run_and_process(argv,
                                             create_update_delete_parse_result,
                                             raw=_raw,
                                             **p4options)
            finally:
                _removeTemporaryForm(formfile)

        def create_change(change, files):
            # Empty 'files' should default to all opened files in the
            # 'default' changelist.
            if files is None:
                files = [{'depotFile': f['depotFile']}
                         for f in self.opened()]
            elif files == []:  # Explicitly specified no files.
                pass
            else:
                #TODO: Add test to expect P4LibError if try to use
                #      p4 wildcards in files. Currently *do* get
                #      correct behaviour.
                files = [{'depotFile': f['depotFile']}
                         for f in self.where(files)]
            form = makeForm(files=files, description=description,
                            change='new')

            return create_update_execute(form)

        def update_change(change, files):
            ch = self.change(change=change)
            if files is None:  # 'files' was not specified.
                pass
            elif files == []:  # Explicitly specified no files.
                # Explicitly specified no files.
                ch['files'] = []
            else:
                depotfiles = [{'depotFile': f['depotFile']}
                              for f in self.where(files)]
                ch['files'] = depotfiles
            if description:
                ch['description'] = description
            form = makeForm(**ch)

            return create_update_execute(form)

        def delete_change(change):
            argv = ['change', '-d', str(change)]

            return self._run_and_process(argv,
                                         create_update_delete_parse_result,
                                         raw=_raw,
                                         **p4options)

        files = _normalizeFiles(files)

        action = None  # note action to know how to parse output below
        if change and files is None and not description:
            if delete:
                return delete_change(change)
            else:
                return get_change_information(change)
        else:
            if delete:
                raise P4LibError("Cannot specify 'delete' with either "
                                 "'files' or 'description'.")
            if change:
                return update_change(change, files)
            elif description:
                return create_change(change, files)

        raise P4LibError("Incomplete/missing arguments.")

    def changes(self, files=[], followIntegrations=False, longOutput=False,
                maximum=None, status=None, _raw=False, **p4options):
        """Return a list of pending and submitted changelists.

        "files" is a list of files or file wildcards that will limit the
            results to changes including these files. Defaults to the
            whole client view.
        "followIntegrations" (-i) specifies to include any changelists
            integrated into the given files.
        "longOutput" (-l) includes changelist descriptions.
        "maximum" (-m) limits the results to the given number of most recent
            relevant changes.
        "status" (-s) limits the output to 'pending' or 'submitted'
            changelists.

        Returns a list of dicts, each representing one change spec. Keys
        are: 'change', 'date', 'client', 'user', 'description'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def changes_parse_cb(output):
            changes = []
            if longOutput:
                changeRe = re.compile("^Change (?P<change>\d+) on "
                                      "(?P<date>[\d/]+) by (?P<user>[^\s@]+)@"
                                      "(?P<client>[^\s@]+)$")

                for line in output.splitlines(True):
                    if not line.strip():
                        continue  # skip blank lines
                    if line.startswith('\t'):
                        # Append this line (minus leading tab) to last
                        # change's description.
                        changes[-1]['description'] += line[1:]
                    else:
                        change = changeRe.match(line).groupdict()
                        change = _values_to_int(change, ['change'])
                        change['description'] = ''
                        changes.append(change)
            else:
                changeRe = re.compile("^Change (?P<change>\d+) on "
                                      "(?P<date>[\d/]+) by (?P<user>[^\s@]+)@"
                                      "(?P<client>[^\s@]+) (\*pending\* )?"
                                      "'(?P<description>.*?)'$")

                all_matches = (_match_or_raise(changeRe, l, "changes")
                               for l in output.splitlines(True))
                changes = [_values_to_int(match.groupdict(), ['change'])
                           for match in all_matches]

            return changes

        if maximum is not None and not isinstance(maximum, int):
            raise P4LibError("Incorrect 'maximum' value. It must be an integer: "
                             "'%s' (type '%s')" % (maximum, type(maximum)))
        if status is not None and status not in ("pending", "submitted"):
            raise P4LibError("Incorrect 'status' value: '%s'" % status)

        optv = _argumentGenerator({'-i': followIntegrations,
                                   '-l': longOutput,
                                   '-m': maximum,
                                   '-s': status})

        argv = ['changes'] + optv
        if files:
            argv += _normalizeFiles(files)

        return self._run_and_process(argv,
                                     changes_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def sync(self, files=[], force=False, dryrun=False, _raw=0, **p4options):
        """Synchronize the client with its view of the depot.
        
        "files" is a list of files or file wildcards to sync. Defaults
            to the whole client view.
        "force" (-f) forces resynchronization even if the client already
            has the file, and clobbers writable files.
        "dryrun" (-n) causes sync to go through the motions and report
            results but not actually make any changes.

        Returns a list of dicts representing the sync'd files. Keys are:
        'depotFile', 'rev', 'comment', and possibly 'notes'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        optv = _argumentGenerator({'-f': force, '-n': dryrun})

        argv = ['sync'] + optv
        results = self._batch_run(argv, _normalizeFiles(files), p4options)

        if _raw:
            return results

        # Forms of output:
        #    //depot/foo#1 - updating C:\foo
        #    //depot/foo#1 - is opened and not being changed
        #    //depot/foo#1 - is opened at a later revision - not changed
        #    //depot/foo#1 - deleted as C:\foo
        #    ... //depot/foo - must resolve #2 before submitting
        # There are probably others forms.
        hits = []
        lineRe = re.compile('^(?P<depotFile>.+?)#(?P<rev>\d+) - '
                            '(?P<comment>.+?)$')

        for line in results["stdout"].splitlines(True):
            if line.startswith('... '):
                note = line.split(' - ')[-1].strip()
                hits[-1]['notes'].append(note)
            else:
                match = _match_or_raise(lineRe, line, "sync")
                if match:
                    hit = match.groupdict()
                    hit = _values_to_int(hit, ['rev'])
                    hit['notes'] = []
                    hits.append(hit)

        return hits

    def edit(self, files, change=None, filetype=None, _raw=0, **p4options):
        """Open an existing file for edit.

        "files" is a list of files or file wildcards to open for edit.
        "change" (-c) is a pending changelist number in which to put the
            opened files.
        "filetype" (-t) specifies to explicitly open the files with the
            given filetype.

        Returns a list of dicts representing commentary on each file
        opened for edit.  Keys are: 'depotFile', 'rev', 'comment', 'notes'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        optv = _argumentGenerator({'-c': change, '-t': filetype})
        
        argv = ['edit'] + optv + _normalizeFiles(files)
        output, error, retval = self._p4run(argv, **p4options)
        if _raw:
            return {'stdout': output, 'stderr': error, 'retval': retval}

        # Example output:
        #   //depot/build.py#142 - opened for edit
        #   ... //depot/build.py - must sync/resolve #143,#148 before submitting
        #   ... //depot/build.py - also opened by davida@davida-bertha
        #   ... //depot/build.py - also opened by davida@davida-loom
        #   ... //depot/build.py - also opened by davida@davida-marteau
        #   ... //depot/build.py - also opened by trentm@trentm-razor
        #
        #   //depot/BuildNum.txt#3 - currently opened for edit
        #
        #   //depot/foo.txt - can't change from change 24940 - use 'reopen'
        #   Returns:
        #    [{"depotFile": "//depot/foo.txt",
        #      "rev": None,
        #      "comment": "can't change from change 24940 - use 'reopen'",
        #      "notes": []}]
        hits = []
        lineRe = re.compile('^(?P<depotFile>.+?)#(?P<rev>\d+) - '
                            '(?P<comment>.*)$')
        line2Re = re.compile('^(?P<depotFile>.+?) - '
                             '(?P<comment>.*)$')
        for line in output.splitlines(True):
            line = line.rstrip()
            if line.startswith("..."):  # this is a note for the latest hit
                note = line.split(' - ')[-1].strip()
                hits[-1]['notes'].append(note)
            else:
                match = lineRe.match(line)
                if not match:
                    match = _match_or_raise(line2Re, line, "edit")

                hit = match.groupdict()
                if 'rev' not in hit:  # line2Re
                    hit['rev'] = None
                hit['notes'] = []
                hits.append(hit)
        return hits

    def add(self, files, change=None, filetype=None, _raw=0, **p4options):
        """Open a new file to add it to the depot.
        
        "files" is a list of files or file wildcards to open for add.
        "change" (-c) is a pending changelist number in which to put the
            opened files.
        "filetype" (-t) specifies to explicitly open the files with the
            given filetype.

        Returns a list of dicts representing commentary on each file
        *attempted* to be opened for add. Keys are: 'depotFile', 'rev',
        'comment', 'notes'. If a given file is NOT added then the 'rev'
        will be None.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def add_parse_cb(output):
            # Example output:
            #   //depot/apps/px/p4.py#1 - opened for add
            #   c:\trentm\apps\px\p4.py - missing, assuming text.
            #
            #   //depot/apps/px/px.py - can't add (already opened for edit)
            #   ... //depot/apps/px/px.py - warning: add of existing file
            #
            #   //depot/apps/px/px.cpp - can't add existing file
            #
            #   //depot/apps/px/t#1 - opened for add
            #
            hits = []
            hitRe = re.compile('^(?P<depotFile>//.+?)(#(?P<rev>\d+))? - '
                               '(?P<comment>.*)$')
            for line in output.splitlines(True):
                match = hitRe.match(line)
                if match:
                    hit = match.groupdict()
                    hit = _values_to_int(hit, ['rev'])
                    hit['notes'] = []
                    hits.append(hit)
                else:
                    if line.startswith("..."):
                        note = line.split(' - ')[-1].strip()
                    else:
                        note = line.strip()
                    hits[-1]['notes'].append(note)
            return hits

        optv = _argumentGenerator({'-c': change, '-t': filetype})
        argv = ['add'] + optv + _normalizeFiles(files)

        return self._run_and_process(argv,
                                     add_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def files(self, files, _raw=0, **p4options):
        """List files in the depot.
        
        "files" is a list of files or file wildcards to list. Defaults
            to the whole client view.

        Returns a list of dicts, each representing one matching file. Keys
        are: 'depotFile', 'rev', 'type', 'change', 'action'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def files_parse_cb(output):
            fileRe = re.compile("^(?P<depotFile>//.*?)#(?P<rev>\d+) - "
                                "(?P<action>\w+) change (?P<change>\d+) "
                                "\((?P<type>[\w+]+)\)$")

            all_matches = (_match_or_raise(fileRe, l, "files")
                           for l in output.splitlines(True))
            hits = [_values_to_int(match.groupdict(), ['rev', 'change'])
                    for match in all_matches]

            return hits

        if not files:
            raise P4LibError("Missing/wrong number of arguments.")

        argv = ['files'] + _normalizeFiles(files)

        return self._run_and_process(argv,
                                     files_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def filelog(self, files, followIntegrations=False, longOutput=False, maxRevs=None,
                _raw=0, **p4options):
        """List revision histories of files.
        
        "files" is a list of files or file wildcards to describe.
        "followIntegrations" (-i) specifies to follow branches.
        "longOutput" (-l) includes changelist descriptions.
        "maxRevs" (-m) limits the results to the given number of
            most recent revisions.

        Returns a list of hits. Each hit is a dict with the following
        keys: 'depotFile', 'revs'. 'revs' is a list of dicts, each
        representing one submitted revision of 'depotFile' and
        containing the following keys: 'action', 'change', 'client',
        'date', 'type', 'notes', 'rev', 'user'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def filelog_parse_cb(output):
            hits = []
            revRe = re.compile("^... #(?P<rev>\d+) change (?P<change>\d+) "
                               "(?P<action>\w+) on (?P<date>[\d/]+) by "
                               "(?P<user>[^\s@]+)@(?P<client>[^\s@]+) "
                               "\((?P<type>[\w+]+)\)( '(?P<description>.*?)')?$")
            for line in output.splitlines(True):
                if longOutput and not line.strip():
                    continue  # skip blank lines
                elif line.startswith('//'):
                    hit = {'depotFile': line.strip(), 'revs': []}
                    hits.append(hit)
                elif line.startswith('... ... '):
                    hits[-1]['revs'][-1]['notes'].append(line[8:].strip())
                elif line.startswith('... '):
                    match = _match_or_raise(revRe, line, "filelog/Internal")
                    d = match.groupdict('')
                    d = _values_to_int(d, ['change', 'rev'])
                    hits[-1]['revs'].append(d)
                    hits[-1]['revs'][-1]['notes'] = []
                elif longOutput and line.startswith('\t'):
                    # Append this line (minus leading tab) to last hit's
                    # last rev's description.
                    hits[-1]['revs'][-1]['description'] += line[1:]
                else:
                    raise P4LibError("Unexpected 'p4 filelog' output: '%s'"
                                     % line)
            return hits

        if maxRevs is not None and not isinstance(maxRevs, int):
            raise P4LibError("Incorrect 'maxRevs' value. It must be an "
                             "integer: '%s' (type '%s')"
                             % (maxRevs, type(maxRevs)))
        if not files:
            raise P4LibError("Missing/wrong number of arguments.")

        optv = _argumentGenerator({'-i': followIntegrations,
                                   '-l': longOutput,
                                   '-m': maxRevs})
        argv = ['filelog'] + optv + _normalizeFiles(files)

        return self._run_and_process(argv,
                                     filelog_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def print_(self, files, localFile=None, quiet=False, **p4options):
        """Retrieve depot file contents.
        
        "files" is a list of files or file wildcards to print.
        "localFile" (-o) is the name of a local file in which to put the
            output text.
        "quiet" (-q) suppresses some file meta-information.

        Returns a list of dicts, each representing one matching file.
        Keys are: 'depotFile', 'rev', 'type', 'change', 'action',
        and 'text'. If 'quiet', the first five keys will not be present.
        The 'text' key will not be present if the file is binary. If
        both 'quiet' and 'localFile', there will be no hits at all.
        """
        if not files:
            raise P4LibError("Missing/wrong number of arguments.")

        optv = _argumentGenerator({'-o': localFile, '-q': quiet})

        # There is *no* way to properly and reliably parse out multiple file
        # output without using -s or -G. Use the latter.
        if p4options:
            d = self.optd
            d.update(p4options)
            p4optv = makeOptv(**d)
        else:
            p4optv = self._optv

        argv = [self.p4, '-G'] + p4optv + ['print'] + \
            optv + _normalizeFiles(files)

        cmd = _joinArgv(argv)
        log.debug("popen3 '%s'..." % cmd)
        i, o, e = os.popen3(cmd)
        hits = []
        fileRe = re.compile("^(?P<depotFile>//.*?)#(?P<rev>\d+) - "
                            "(?P<action>\w+) change (?P<change>\d+) "
                            "\((?P<type>[\w+]+)\)$")
        try:
            startHitWithNextNode = 1
            while 1:
                node = marshal.load(o)
                if node['code'] == 'info':
                    # Always start a new hit with an 'info' node.
                    match = fileRe.match(node['data'])
                    hit = match.groupdict()
                    hit = _values_to_int(hit, ['change', 'rev'])
                    hits.append(hit)
                    startHitWithNextNode = 0
                elif node['code'] == 'text':
                    if startHitWithNextNode:
                        hit = {'text': node['data']}
                        hits.append(hit)
                    else:
                        if 'text' not in hits[-1] \
                           or hits[-1]['text'] is None:
                            hits[-1]['text'] = node['data']
                        else:
                            hits[-1]['text'] += node['data']
                    startHitWithNextNode = not node['data']
        except EOFError:
            pass
        return hits

    def diff(self, files=[], diffFormat='', force=False, satisfying=None,
             text=False, _raw=0, **p4options):
        """Display diff of client files with depot files.
        
        "files" is a list of files or file wildcards to diff.
        "diffFormat" (-d<flag>) is a flag to pass to the built-in diff
            routine to control the output format. Valid values are ''
            (plain, default), 'n' (RCS), 'c' (context), 's' (summary),
            'u' (unified).
        "force" (-f) forces a diff of every file.
        "satifying" (-s<flag>) limits the output to the names of files
            satisfying certain criteria:
               'a'     Opened files that are different than the revision
                       in the depot, or missing.
               'd'     Unopened files that are missing on the client.
               'e'     Unopened files that are different than the
                       revision in the depot.
               'r'     Opened files that are the same as the revision in
                       the depot.
        "text" (-t) forces diffs of non-text files.

        Returns a list of dicts representing each file diff'd. If
        "satifying" is specified each dict will simply include a
        'localFile' key. Otherwise, each dict will include 'localFile',
        'depotFile', 'rev', and 'binary' (boolean) keys and possibly a
        'text' or a 'notes' key iff there are any differences. Generally
        you will get a 'notes' key for differing binary files.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        if diffFormat not in ('', 'n', 'c', 's', 'u'):
            raise P4LibError("Incorrect diff format flag: '%s'" % diffFormat)
        if satisfying is not None\
           and satisfying not in ('a', 'd', 'e', 'r'):
            raise P4LibError("Incorrect 'satisfying' flag: '%s'" % satisfying)

        optv = _argumentGenerator({'-d%s': diffFormat,
                                   '-s%s': satisfying,
                                   '-f': force,
                                   '-t': text})

        # There is *no* to properly and reliably parse out multiple file
        # output without using -s or -G. Use the latter. (XXX Huh?)
        argv = ['diff'] + optv + _normalizeFiles(files)

        if satisfying is not None:
            diff_parse_cb = lambda output: \
                [{'localFile': line[:-1]} for line in output.splitlines(True)]
        else:
            diff_parse_cb = _parseDiffOutput

        return self._run_and_process(argv,
                                     diff_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def diff2(self, file1, file2, diffFormat='', quiet=True, text=0,
              **p4options):
        """Compare two depot files.
        
        "file1" and "file2" are the two files to diff.
        "diffFormat" (-d<flag>) is a flag to pass to the built-in diff
            routine to control the output format. Valid values are ''
            (plain, default), 'n' (RCS), 'c' (context), 's' (summary),
            'u' (unified).
        "quiet" (-q) suppresses some meta information and all
            information if the files do not differ.

        Returns a dict representing the diff. Keys are: 'depotFile1',
        'rev1', 'type1', 'depotFile2', 'rev2', 'type2',
        'summary', 'notes', 'text'. There may not be a 'text' key if the
        files are the same or are binary. The first eight keys will not
        be present if 'quiet'.

        Note that the second 'p4 diff2' style is not supported:
            p4 diff2 [ -d<flag> -q -t ] -b branch [ [ file1 ] file2 ]
        """
        if diffFormat not in ('', 'n', 'c', 's', 'u'):
            raise P4LibError("Incorrect diff format flag: '%s'" % diffFormat)

        optv = _argumentGenerator({'-d%s': diffFormat,
                                   '-q': quiet,
                                   '-t': text})

        # There is *no* way to properly and reliably parse out multiple
        # file output without using -s or -G. Use the latter.
        if p4options:
            d = self.optd
            d.update(p4options)
            p4optv = makeOptv(**d)
        else:
            p4optv = self._optv
        argv = [self.p4, '-G'] + p4optv + ['diff2'] + optv + [file1, file2]
        cmd = _joinArgv(argv)
        i, o, e = os.popen3(cmd)
        diff = {}
        infoRe = re.compile("^==== (?P<depotFile1>.+?)#(?P<rev1>\d+) "
                            "\((?P<type1>[\w+]+)\) - "
                            "(?P<depotFile2>.+?)#(?P<rev2>\d+) "
                            "\((?P<type2>[\w+]+)\) "
                            "==== (?P<summary>\w+)$")
        try:
            while 1:
                node = marshal.load(o)
                if node['code'] == 'info'\
                   and node['data'] == '(... files differ ...)':
                    if 'notes' not in diff:
                        diff['notes'].append(node['data'])
                    else:
                        diff['notes'] = [node['data']]
                elif node['code'] == 'info':
                    match = infoRe.match(node['data'])
                    d = match.groupdict()
                    d['rev1'] = int(d['rev1'])
                    d['rev2'] = int(d['rev2'])
                    diff.update(match.groupdict())
                elif node['code'] == 'text':
                    if 'text' not in diff or diff['text'] is None:
                        diff['text'] = node['data']
                    else:
                        diff['text'] += node['data']
        except EOFError:
            pass
        return diff

    def revert(self, files=[], change=None, unchangedOnly=False, _raw=0,
               **p4options):
        """Discard changes for the given opened files.
        
        "files" is a list of files or file wildcards to revert. If
            'unchangedOnly' is true, then this defaults to the
            whole client view.
        "change" (-c) will limit to files opened in the given
            changelist.
        "unchangedOnly" (-a) will only revert opened files that are not
            different than the version in the depot.

        Returns a list of dicts representing commentary on each file
        reverted.  Keys are: 'depotFile', 'rev', 'comment'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def revert_parse_cb(output):
            # Example output:
            #   //depot/hello.txt#1 - was edit, reverted
            #   //depot/test_g.txt#none - was add, abandoned
            hitRe = re.compile('^(?P<depotFile>//.+?)(#(?P<rev>\w+))? - '
                               '(?P<comment>.*)$')

            all_matches = (_match_or_raise(hitRe, l, "revert")
                           for l in output.splitlines(True))
            hits = [_values_to_int(match.groupdict(), ["rev"])
                    for match in all_matches]

            return hits

        if not unchangedOnly and not files:
            raise P4LibError("Missing/wrong number of arguments.")

        optv = _argumentGenerator({'-c': change, '-a': unchangedOnly})
        argv = ['revert'] + optv + _normalizeFiles(files)

        return self._run_and_process(argv,
                                     revert_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def resolve(self, files=[], autoMode='', force=False, dryrun=False,
                text=False, verbose=False, _raw=False, **p4options):
        """Merge open files with other revisions or files.

        This resolve, for obvious reasons, only supports the options to
        'p4 resolve' that will result is *no* command line interaction.

        'files' is a list of files, of file wildcards, to resolve.
        'autoMode' (-a*) tells how to resolve merges. See below for
            valid values.
        'force' (-f) allows previously resolved files to be resolved again.
        'dryrun' (-n) lists the integrations that *would* be performed
            without performing them.
        'text' (-t) will force a textual merge, even for binary file types.
        'verbose' (-v) will cause markers to be placed in all changed
            files not just those that conflict.

        Valid values of 'autoMode' are:
            ''              '-a' I believe this is equivalent to '-am'.
            'f', 'force'    '-af' Force acceptance of merged files with
                            conflicts.
            'm', 'merge'    '-am' Attempts to merge.
            's', 'safe'     '-as' Does not attempt to merge.
            't', 'theirs'   '-at' Accepts "their" changes, OVERWRITING yours.
            'y', 'yours'    '-ay' Accepts your changes, OVERWRITING "theirs".
        Invalid values of 'autoMode':
            None            As if no -a option had been specified.
                            Invalid because this may result in command
                            line interaction.

        Returns a list of dicts representing commentary on each file for
        which a resolve was attempted. Keys are: 'localFile', 'clientFile'
        'comment', and 'action'; and possibly 'diff chunks' if there was
        anything to merge.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        if autoMode is None:
            raise P4LibError("'autoMode' must be non-None, otherwise "
                             "'p4 resolve' may initiate command line "
                             "interaction, which will hang this method.")

        optv = _argumentGenerator({'-f': force,
                                   '-n': dryrun,
                                   '-t': text,
                                   '-v': verbose})
        # '-a' only is valid
        optv = ['-a%s' % autoMode] + optv

        argv = ['resolve'] + optv

        results = {"stdout": '', "stderr": '', "retval": 0}
        results = self._batch_run(argv, _normalizeFiles(files), p4options)

        if _raw:
            return results

        hits = []
        # Example output:
        #   C:\rootdir\foo.txt - merging //depot/foo.txt#2
        #   Diff chunks: 0 yours + 0 theirs + 0 both + 1 conflicting
        #   //client-name/foo.txt - resolve skipped.
        # Proposed result:
        #   [{'localFile': 'C:\\rootdir\\foo.txt',
        #     'depotFile': '//depot/foo.txt',
        #     'rev': 2
        #     'clientFile': '//client-name/foo.txt',
        #     'diff chunks': {'yours': 0, 'theirs': 0, 'both': 0,
        #                     'conflicting': 1}
        #     'action': 'resolve skipped'}]
        #
        # Example output:
        #   C:\rootdir\foo.txt - vs //depot/foo.txt#2
        #   //client-name/foo.txt - ignored //depot/foo.txt
        # Proposed result:
        #   [{'localFile': 'C:\\rootdir\\foo.txt',
        #     'depotFile': '//depot/foo.txt',
        #     'rev': 2
        #     'clientFile': '//client-name/foo.txt',
        #     'diff chunks': {'yours': 0, 'theirs': 0, 'both': 0,
        #                     'conflicting': 1}
        #     'action': 'ignored //depot/foo.txt'}]
        #
        # Example output (see tm-bug for this):
        #   Non-text diff: 0 yours + 1 theirs + 0 both + 0 conflicting
        introRe = re.compile('^(?P<localFile>.+?) - (merging|vs) '
                             '(?P<depotFile>//.+?)#(?P<rev>\d+)$')
        diffRe = re.compile('^(Diff chunks|Non-text diff): '
                            '(?P<yours>\d+) yours \+ '
                            '(?P<theirs>\d+) theirs \+ (?P<both>\d+) both '
                            '\+ (?P<conflicting>\d+) conflicting$')
        actionRe = re.compile('^(?P<clientFile>//.+?) - (?P<action>.+?)(\.)?$')
        for line in results["stdout"].splitlines(True):
            match = introRe.match(line)
            if match:
                hit = match.groupdict()
                hit = _values_to_int(hit, ["rev"])
                hits.append(hit)
                log.info("parsed resolve 'intro' line: '%s'" % line.strip())
                continue
            match = diffRe.match(line)
            if match:
                diff = match.groupdict()
                diff = _values_to_int(diff,
                                      ["yours", "theirs",
                                       "both", "conflicting"])
                hits[-1]['diff chunks'] = diff
                log.info("parsed resolve 'diff' line: '%s'" % line.strip())
                continue
            match = actionRe.match(line)
            if match:
                hits[-1].update(match.groupdict())
                log.info("parsed resolve 'action' line: '%s'" % line.strip())
                continue
            raise P4LibError("Internal error: could not parse 'p4 resolve' "
                             "output line: line='%s' argv=%s" % (line, argv))
        return hits

    def submit(self, files=None, description=None, change=None, _raw=0,
               **p4options):
        """Submit open files to the depot.

        There are two ways to call this method:
            - Submit specific files:
                p4.submit([...], "checkin message")
            - Submit a pending changelist:
                p4.submit(change=123)
              Note: 'change' should always be specified with a keyword
              argument. I reserve the right to extend this method by
              adding kwargs *before* the change arg. So p4.submit(None,
              None, 123) is not guaranteed to work.

        Returns a dict with a 'files' key (which is a list of dicts with
        'depotFile', 'rev', and 'action' keys), and 'action'
        (=='submitted') and 'change' keys iff the submit is succesful.

        Note: An equivalent for the '-s' option to 'p4 submit' is not
        supported, because I don't know how to use it and have never.
        Nor is the '-i' option supported, although it *is* used
        internally to drive 'p4 submit'.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        #TODO:
        #   - test when submission fails because files need to be
        #     resolved
        #   - Structure this code more like change, client, label, & branch.
        formfile = None
        try:
            files = _normalizeFiles(files)

            if change and not files and not description:
                argv = ['submit', '-c', str(change)]
            elif not change and files is not None and description:
                # Empty 'files' should default to all opened files in the
                # 'default' changelist.
                if not files:
                    files = [{'depotFile': f['depotFile']}
                             for f in self.opened()]
                else:
                    #TODO: Add test to expect P4LibError if try to use
                    #      p4 wildcards in files.
                    files = [{'depotFile': f['depotFile']}
                             for f in self.where(files)]
                # Build submission form file.
                form = makeForm(files=files, description=description,
                                change='new')
                formfile = _writeTemporaryForm(form)
                argv = ['submit', '-i', '<', formfile]
            else:
                raise P4LibError("Incorrect arguments. You must specify "
                                 "'change' OR you must specify 'files' and "
                                 "'description'.")

            output, error, retval = self._p4run(argv, **p4options)
            if _raw:
                return {'stdout': output, 'stderr': error, 'retval': retval}

            # Example output:
            #    Change 1 created with 1 open file(s).
            #    Submitting change 1.
            #    Locking 1 files ...
            #    add //depot/test_simple_submit.txt#1
            #    Change 1 submitted.
            #    //depot/test_simple_submit.txt#1 - refreshing
            #
            # Note: That last line only if there are keywords to expand in the
            # submitted file.
            #
            # This returns (similar to .change() output):
            #    {'change': 1,
            #     'action': 'submitted',
            #     'files': [{'depotFile': '//depot/test_simple_submit.txt',
            #                'rev': 1,
            #                'action': 'add'}]}
            # i.e. only the file actions and the last "submitted" line are
            # looked for.
            skipRes = [
                re.compile('^Change \d+ created with \d+ open file\(s\)\.$'),
                re.compile('^Submitting change \d+\.$'),
                re.compile('^Locking \d+ files \.\.\.$'),
                re.compile('^(//.+?)#\d+ - refreshing$'),
            ]
            fileRe = re.compile('^(?P<action>\w+) (?P<depotFile>//.+?)'
                                '#(?P<rev>\d+)$')
            resultRe = re.compile('^Change (?P<change>\d+) '
                                  '(?P<action>submitted)\.')
            result = {'files': []}
            for line in output.splitlines(True):
                match = fileRe.match(line)
                if match:
                    file = match.groupdict()
                    file['rev'] = int(file['rev'])
                    result['files'].append(file)
                    log.info("parsed submit 'file' line: '%s'", line.strip())
                    continue
                match = resultRe.match(line)
                if match:
                    result.update(match.groupdict())
                    result['change'] = int(result['change'])
                    log.info("parsed submit 'result' line: '%s'",
                             line.strip())
                    continue
                # The following is technically just overhead but it is
                # considered more robust if we explicitly try to recognize
                # all output. Unrecognized output can be warned or raised.
                for skipRe in skipRes:
                    match = skipRe.match(line)
                    if match:
                        log.info("parsed submit 'skip' line: '%s'",
                                 line.strip())
                        break
                else:
                    log.warn("Unrecognized output line from running %s: "
                             "'%s'. Please report this to the maintainer."
                             % (argv, line))
            return result
        finally:
            _removeTemporaryForm(formfile)

    def delete(self, files, change=None, _raw=0, **p4options):
        """Open an existing file to delete it from the depot.

        "files" is a list of files or file wildcards to open for delete.
        "change" (-c) is a pending change with which to associate the
            opened file(s).

        Returns a list of dicts each representing a file *attempted* to
        be open for delete. Keys are 'depotFile', 'rev', and 'comment'.
        If the file could *not* be openned for delete then 'rev' will be
        None.

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def delete_parse_cb(output):
            # Example output:
            #   //depot/foo.txt#1 - opened for delete
            #   //depot/foo.txt - can't delete (already opened for edit)
            hitRe = re.compile('^(?P<depotFile>.+?)(#(?P<rev>\d+))? - '
                               '(?P<comment>.*)$')

            all_matches = (_match_or_raise(hitRe, l, "delete")
                           for l in output.splitlines(True))
            hits = [_values_to_int(match.groupdict(), ["rev"])
                    for match in all_matches]

            return hits

        optv = _argumentGenerator({'-c': change})
        argv = ['delete'] + optv + _normalizeFiles(files)

        return self._run_and_process(argv,
                                     delete_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def client(self, name=None, client=None, delete=0, _raw=0, **p4options):
        """Create, update, delete, or get a client specification.
        
        Creating a new client spec or updating an existing one:
            p4.client(client=<client dictionary>)
                          OR
            p4.client(name=<an existing client name>,
                      client=<client dictionary>)
        Returns a dictionary of the following form:
            {'client': <clientname>, 'action': <action taken>}

        Deleting a client spec:
            p4.client(name=<an existing client name>, delete=1)
        Returns a dictionary of the following form:
            {'client': <clientname>, 'action': 'deleted'}

        Getting a client spec:
            ch = p4.client(name=<an existing client name>)
        Returns a dictionary describing the client. For example:
            {'access': '2002/07/16 00:05:31',
             'client': 'trentm-ra',
             'description': 'Created by trentm.',
             'host': 'ra',
             'lineend': 'local',
             'options': 'noallwrite noclobber nocompress unlocked nomodtime normdir',
             'owner': 'trentm',
             'root': 'c:\\trentm\\',
             'update': '2002/03/18 22:33:18',
             'view': '//depot/... //trentm-ra/...'}

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}

        Limitations: The -f (force) and -t (template) flags are not
        supported. However, there is no strong need to support -t
        because the use of dictionaries in this API makes this trivial.
        """
        def get_client_information(name):
            argv = ['client', '-o', name]

            return self._run_and_process(argv,
                                         parseForm,
                                         raw=_raw,
                                         **p4options)

        def create_update_delete_parse_result(output):
            lines = output.splitlines(True)
            # Example output:
            #   Client trentm-ra not changed.
            #   Client bertha-test deleted.
            #   Client bertha-test saved.
            resultRe = re.compile("^Client (?P<client>[^\s@]+)"
                                  " (?P<action>not changed|deleted|saved)\.$")

            match = _match_or_raise(resultRe, lines[0], "client")
            return match.groupdict()

        def create_update_client(name, client):
            if 'client' in client:
                name = client["client"]
            if name is not None:
                cl = self.client(name=name)
            else:
                cl = {}
            cl.update(client)
            form = makeForm(**cl)

            try:
                # Build submission form file.
                formfile = _writeTemporaryForm(form)
                argv = ['client', '-i', '<', formfile]

                return self._run_and_process(argv,
                                             create_update_delete_parse_result,
                                             raw=_raw,
                                             **p4options)
            finally:
                _removeTemporaryForm(formfile)

        def delete_client(name):
            argv = ['client', '-d', name]

            return self._run_and_process(argv,
                                         create_update_delete_parse_result,
                                         raw=_raw,
                                         **p4options)

        if delete:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of client to delete.")
            return delete_client(name)
        elif client is None:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of client to get.")
            return get_client_information(name)
        else:
            return create_update_client(name, client)

    def clients(self, _raw=0, **p4options):
        """Return a list of clients.

        Returns a list of dicts, each representing one client spec, e.g.:
            [{'client': 'trentm-ra',        # client name
              'update': '2002/03/18',       # client last modification date
              'root': 'c:\\trentm\\',       # the client root directory
              'description': 'Created by trentm. '},
                                        # *part* of the client description
             ...
            ]

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def clients_parse_cb(output):
            # Examples:
            # Client trentm-ra 2002/03/18 root c:\trentm\ 'Created by trentm. '
            clientRe = re.compile("^Client (?P<client>[^\s@]+) "
                                  "(?P<update>[\d/]+) "
                                  "root (?P<root>.*?) '(?P<description>.*?)'$")

            all_matches = (_match_or_raise(clientRe, l, "clients")
                           for l in output.splitlines(True))
            clients = [match.groupdict() for match in all_matches]

            return clients

        argv = ['clients']

        return self._run_and_process(argv,
                                     clients_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def label(self, name=None, label=None, delete=0, _raw=0, **p4options):
        r"""Create, update, delete, or get a label specification.
        
        Creating a new label spec or updating an existing one:
            p4.label(label=<label dictionary>)
                          OR
            p4.label(name=<an existing label name>,
                     label=<label dictionary>)
        Returns a dictionary of the following form:
            {'label': <labelname>, 'action': <action taken>}

        Deleting a label spec:
            p4.label(name=<an existing label name>, delete=1)
        Returns a dictionary of the following form:
            {'label': <labelname>, 'action': 'deleted'}

        Getting a label spec:
            ch = p4.label(name=<an existing label name>)
        Returns a dictionary describing the label. For example:
            {'access': '2001/07/13 10:42:32',
             'description': 'ActivePerl 623',
             'label': 'ActivePerl_623',
             'options': 'locked',
             'owner': 'daves',
             'update': '2000/12/15 20:15:48',
             'view': '//depot/main/Apps/ActivePerl/...\n//depot/main/support/...'}

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}

        Limitations: The -f (force) and -t (template) flags are not
        supported. However, there is no strong need to support -t
        because the use of dictionaries in this API makes this trivial.
        """
        def get_label_information(name):
            argv = ['label', '-o', name]

            return self._run_and_process(argv,
                                         parseForm,
                                         raw=_raw,
                                         **p4options)

        def create_update_delete_parse_result(output):
            lines = output.splitlines(True)
            # Example output:
            #   Label label_1 not changed.
            #   Label label_2 deleted.
            #   Label label_3 saved.
            resultRe = re.compile("^Label (?P<label>[^\s@]+)"
                                  " (?P<action>not changed|deleted|saved)\.$")

            match = _match_or_raise(resultRe, lines[0], "label")
            match = resultRe.match(lines[0])

            return match.groupdict()

        def create_update_label(name, label):
            if 'label' in label:
                name = label["label"]
            if name is not None:
                lbl = self.label(name=name)
            else:
                lbl = {}
            lbl.update(label)
            form = makeForm(**lbl)

            try:
                # Build submission form file.
                formfile = _writeTemporaryForm(form)
                argv = ['label', '-i', '<', formfile]

                return self._run_and_process(argv,
                                             create_update_delete_parse_result,
                                             raw=_raw,
                                             **p4options)
            finally:
                _removeTemporaryForm(formfile)

        def delete_label(name):
            argv = ['label', '-d', name]

            return self._run_and_process(argv,
                                         create_update_delete_parse_result,
                                         raw=_raw,
                                         **p4options)

        if delete:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of label to delete.")
            return delete_label(name)
        elif label is None:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of label to get.")
            return get_label_information(name)
        else:
            return create_update_label(name, label)

    def labels(self, _raw=0, **p4options):
        """Return a list of labels.

        Returns a list of dicts, each representing one labels spec, e.g.:
            [{'label': 'ActivePerl_623', # label name
              'description': 'ActivePerl 623 ',
                                         # *part* of the label description
              'update': '2000/12/15'},   # label last modification date
             ...
            ]

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def labels_parse_cb(output):
            labelRe = re.compile("^Label (?P<label>[^\s@]+) "
                                 "(?P<update>[\d/]+) "
                                 "'(?P<description>.*?)'$")

            all_matches = (_match_or_raise(labelRe, l, "labels")
                           for l in output.splitlines(True))
            labels = [match.groupdict() for match in all_matches]

            return labels

        argv = ['labels']

        return self._run_and_process(argv,
                                     labels_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def flush(self, files=[], force=False, dryrun=False, _raw=False, **p4options):
        """Fake a 'sync' by not moving files.
        
        "files" is a list of files or file wildcards to flush. Defaults
            to the whole client view.
        "force" (-f) forces resynchronization even if the client already
            has the file, and clobbers writable files.
        "dryrun" (-n) causes sync to go through the motions and report
            results but not actually make any changes.

        Returns a list of dicts representing the flush'd files. For
        example:
            [{'comment': 'added as C:\\...\\foo.txt',
              'depotFile': '//depot/.../foo.txt',
              'notes': [],
              'rev': 1},
             {'comment': 'added as C:\\...\\bar.txt',
              'depotFile': '//depot/.../bar.txt',
              'notes': [],
              'rev': 1},
            ]

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def flush_parse_cb(output):
            # Forms of output:
            #    //depot/foo#1 - updating C:\foo
            #    //depot/foo#1 - is opened and not being changed
            #    //depot/foo#1 - is opened at a later revision - not changed
            #    //depot/foo#1 - deleted as C:\foo
            #    ... //depot/foo - must resolve #2 before submitting
            # There are probably others forms.
            hits = []
            lineRe = re.compile('^(?P<depotFile>.+?)#(?P<rev>\d+) - '
                                '(?P<comment>.+?)$')
            for line in output.splitlines(True):
                if line.startswith('... '):
                    note = line.split(' - ')[-1].strip()
                    hits[-1]['notes'].append(note)
                else:
                    match = _match_or_raise(lineRe, line, "flush")
                    hit = match.groupdict()
                    hit = _values_to_int(hit, ['rev'])
                    hit['notes'] = []
                    hits.append(hit)

            return hits

        optv = _argumentGenerator({'-f': force,
                                   '-n': dryrun})

        argv = ['flush'] + optv
        if files:
            argv += _normalizeFiles(files)

        return self._run_and_process(argv,
                                     flush_parse_cb,
                                     raw=_raw,
                                     **p4options)

    def branch(self, name=None, branch=None, delete=0, _raw=0, **p4options):
        r"""Create, update, delete, or get a branch specification.
        
        Creating a new branch spec or updating an existing one:
            p4.branch(branch=<branch dictionary>)
                          OR
            p4.branch(name=<an existing branch name>,
                     branch=<branch dictionary>)
        Returns a dictionary of the following form:
            {'branch': <branchname>, 'action': <action taken>}

        Deleting a branch spec:
            p4.branch(name=<an existing branch name>, delete=1)
        Returns a dictionary of the following form:
            {'branch': <branchname>, 'action': 'deleted'}

        Getting a branch spec:
            ch = p4.branch(name=<an existing branch name>)
        Returns a dictionary describing the branch. For example:
            {'access': '2000/12/01 16:54:57',
             'branch': 'trentm-roundup',
             'description': 'Branch ...',
             'options': 'unlocked',
             'owner': 'trentm',
             'update': '2000/12/01 16:54:57',
             'view': '//depot/foo/... //depot/bar...'}

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}

        Limitations: The -f (force) and -t (template) flags are not
        supported. However, there is no strong need to support -t
        because the use of dictionaries in this API makes this trivial.
        """
        def delete_create_update_result(output):
            lines = output.splitlines(True)
            # Example output:
            #   Branch trentm-ra not changed.
            #   Branch bertha-test deleted.
            #   Branch bertha-test saved.
            resultRe = re.compile("^Branch (?P<branch>[^\s@]+)"
                                  " (?P<action>not changed|deleted|saved)\.$")

            match = _match_or_raise(resultRe, lines[0], 'branch')
            return match.groupdict()

        def get_branch_info(name):
            argv = ['branch', '-o', name]

            return self._run_and_process(argv,
                                         parseForm,
                                         raw=_raw,
                                         **p4options)

        def delete_branch(name):
            argv = ['branch', '-d', name]

            return self._run_and_process(argv,
                                         delete_create_update_result,
                                         raw=_raw,
                                         **p4options)

        def create_update_branch(name, branch):
            if 'branch' in branch:
                name = branch["branch"]
            if name is not None:
                br = self.branch(name=name)
            else:
                br = {}
            br.update(branch)
            form = makeForm(**br)

            try:
                formfile = _writeTemporaryForm(form)
                argv = ['branch', '-i', '<', formfile]

                output, error, retval = self._p4run(argv, **p4options)
            finally:
                _removeTemporaryForm(formfile)

            if _raw:
                return {'stdout': output, 'stderr': error, 'retval': retval}

            return delete_create_update_result(output)

        if delete:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of branch to delete.")
            return delete_branch(name)
        elif branch is None:
            if name is None:
                raise P4LibError("Incomplete/missing arguments: must "
                                 "specify 'name' of branch to get.")
            return get_branch_info(name)
        else:
            return create_update_branch(name, branch)

    def branches(self, _raw=0, **p4options):
        """Return a list of branches.

        Returns a list of dicts, each representing one branches spec,
        e.g.:
            [{'branch': 'zope-aspn',
              'description': 'Contrib Zope into ASPN ',
              'update': '2001/10/15'},
             ...
            ]

        If '_raw' is true then the return value is simply a dictionary
        with the unprocessed results of calling p4:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        def branches_result_cb(output):
            branchRe = re.compile("^Branch (?P<branch>[^\s@]+) "
                                  "(?P<update>[\d/]+) "
                                  "'(?P<description>.*?)'$")

            all_matches = (_match_or_raise(branchRe, l, "branches")
                           for l in output.splitlines(True))
            branches = [match.groupdict() for match in all_matches]

            return branches

        argv = ['branches']

        return self._run_and_process(argv,
                                     branches_result_cb,
                                     raw=_raw,
                                     **p4options)

    def fstat(self, files, _raw=0, **p4options):
        """List files in the depot.
        
        "files" is a list of files or file wildcards to list. Defaults
            to the whole client view.

        Returns a dict containing the following keys:

                clientFile      -- local path (host or Perforce syntax)
                depotFile       -- name in depot
                path            -- local path (host syntax)
                headAction      -- action at head rev, if in depot
                headChange      -- head rev changelist#, if in depot
                headRev         -- head rev #, if in depot
                headType        -- head rev type, if in depot
                headTime        -- head rev mod time, if in depot
                haveRev         -- rev had on client, if on client
                action          -- open action, if opened
                actionOwner     -- user who opened file, if opened
                change          -- open changelist#, if opened
                unresolved      -- unresolved integration records
                ourLock         -- set if this user/client has it locked

        Level 2 information is not returned at this time
        
                otherOpen       -- set if someone else has it open
                otherOpen#      -- list of user@client with file opened
                otherLock       -- set if someone else has it locked
                otherLock#      -- user@client with file locked
                otherAction#    -- open action, if opened by someone else

        See 'p4 help command fstat' for more information.
        
        If '_raw' is true then the a dictionary with the unprocessed
        results of calling p4 is returned in addition to the processed
        results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        _baseStat = {'clientFile': '',
                     'depotFile': '',
                     'path': '',
                     'headAction': '',
                     'headChange': 0,
                     'headRev': 0,
                     'headType': '',
                     'headTime': 0,
                     'haveRev': 0,
                     'action': '',
                     'actionOwner': '',
                     'change': '',
                     'unresolved': '',
                     'ourLock': 0,
                     }

        def match_file_block(stat):
            matches = fileRe.findall(stat)
            if not matches:
                return None

            matches = dict(matches)

            hit = copy.copy(_baseStat)
            hit.update(matches)

            if 'ourLock' in matches:
                hit['ourLock'] = 1

            int_keys = ('headChange', 'headRev', 'headTime', 'haveRev')
            hit = _values_to_int(hit, int_keys)

            return hit

        if not files:
            raise P4LibError("Missing/wrong number of arguments.")

        argv = ['fstat', '-C', '-P'] + _normalizeFiles(files)
        output, error, retval = self._p4run(argv, **p4options)

        parsed = ''.join(output)
        parsed = re.split(r'(\r\n|\n){2}', parsed)
        
        fileRe = re.compile("...\s(.*?)\s(.*)")
        
        all_stats = (match_file_block(stat) for stat in parsed)
        hits = [hit for hit in all_stats if hit]

        if _raw:
            return hits, {'stdout': ''.join(output),
                          'stderr': ''.join(error),
                          'retval': retval}
        else:
            return hits
