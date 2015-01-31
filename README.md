p4lib status
------------

Mature; has been heavily used in a commercial product for
over 3 years. Limited in the coverage of the Perforce Client
API.

This fork in compatible with both Python 2.7 and Python 3.4.
Might be compatible with other Python 3.x versions.

Compatibility with Python 3 starts with v0.9.6

px status
---------

Hasn't been updated in a while so is showing its age in
some places (e.g. 'px annotate' was added before p4 grew an
annotate command).

px has not been updated after v0.9.5 and is probably not working starting
with version v0.9.6.

px
----------------

Perforce is a source code control system (like CVS or Subversion).
The standard command-line command for working with Perforce is `p4`.
`px` is a wrapper around `p4`.  It provides all the functionality of p4
(defering work to it) plus it extends some standard p4 commands and
adds a few new ones. If you are a Perforce user you might find these
extensions useful.


p4lib
-----

`p4lib.py` is a Python interface to the Perforce client
application.  If you are a Python programmer and script Perforce you
might find this module helpful. Currently, most common commands (though
your definition of "common" may differ from mine) are supported. The
`p4lib.py` module docstring says exactly which -- read it
[TODO/url/to/p4lib.py here] or run:

    pydoc p4lib

Note: `p4lib.py` is a pure-Python wrapper that shells-out to `p4`. I.e.
it is not using Perforce's C++ P4Client API. This has the benefit of not
requiring binary builds (hence works on a lot of platforms easily) and
the drawback of not automatically supporting the whole set of `p4`
client commands. 

An unrelated benefit of `p4lib.py` is that it attempts to provide a
somewhat Pythonic interface to the p4 client commands. YMMV.



### Getting Started with `p4lib.py`

If you do any Python scripting of Perforce, then `p4lib.py` might be of
interest to you. As mentioned above, not *all* Perforce client API
commands are supported so you should make sure it has the ones you need
first. The `p4lib.py` module docstring will tell you:

    pydoc p4lib

All interaction is done via a "P4" instance:

    >>> import p4lib
    >>> p4 = p4lib.P4(OPTIONS)
    >>> result = p4.COMMAND(OPTIONS)

For example, to open a file for editing:

    >>> import p4lib
    >>> p4 = p4lib.P4()
    >>> p4.edit("cb.py")
    [{'comment': 'opened for edit', 
      'notes': [], 
      'rev': 77, 
      'depotFile': '//depot/main/Apps/Komodo-devel/src/codeintel/cb.py'}]

To verify that that file was actually opened:

    >>> p4.opened("./...")
    [{'rev': 77, 
      'action': 'edit', 
      'type': 'text', 
      'depotFile': '//depot/main/Apps/Komodo-devel/src/codeintel/cb.py', 
      'change': 'default'}]

The docstrings for each command should describe all you need to know to
use them. Either read `pydoc` output:

    pydoc p4lib

or play around in the interactive shell:

    >>> help(p4.edit)


### Getting Started with `px`

As with the `p4` command itself, the built-in documentation for `px` is
pretty good. (Please send me [feedback](mailto:trentm@activestate.com)
if you find this isn't true!) `px` should feel and act like using `p4`.
To see the `px` extensions, enter `px help px`:

    $ px help px
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

Personally, the extensions that I find most useful are:

1. `px changes -d`

   This is very useful for grepping through a lot of changes to a
   particular file or area. For example:

        px changes -d ./... | less

2. `px backout CHANGENUM`

   The full procedure for backing out a check-in to Perforce is
   described in [Tech Note 14](http://www.perforce.com/perforce/technotes/note014.html).
   This can be tedious to work through. `px backout` does a decent job
   of handling all these steps for you.

3. `px diff -sn`

   Ever want to know what new files in your client area you've
   forgotten to `p4 add`. This will tell you. 

   Also, this command simplifies the instructions for [Perforce Tech Note
   12](http://www.perforce.com/perforce/technotes/note012.html) for
   importing a directory tree and part of [Tech Note
   2](http://www.perforce.com/perforce/technotes/note002.html) for
   working offline to not have to give platform-specific commands:

        px diff -sn ./... | px -x - add
        px diff -sd ./... | px -x - delete
        px diff -se ./... | px -x - edit




Change Log
----------

### v0.9.6

- First version compatible with Python 2.7 and Python 3.4.
- Arguments designing switches now take boolean and no more 0/1 int values.
  This is a breaking change if you used 0/1 int values, as the command won't
  take them. If you already used boolean values, leaning on the fact that
  True/False are converted to 1/0, then you're safe.
- p4lib can add() files with the p4 restricted '@' char.

### v0.9.5
- Fix a problem identified by "j w" where
  `p4.edit(<path>, change=123)` would fail if the path was already
  open and part of another pending change.
- Fixes for 'p4 fstat' parsing if process output uses '\r\n' EOLs.
- Fix http://bugs.activestate.com/show_bug.cgi?id=73103 (Perforce
  submit form does not match same submit from command line).

### v0.9.4
- Diff output parsing fix.
- `p4 describe` output parsing fix.

### v0.9.3
- Add `p4.fstat()`.

### v0.9.2
- A fix from Aku Levola so that 'p4 diff -sn ./...' works with
  filenames that have a '#' in them.

### v0.9.1
- Fix shebang line in 'px'

### v0.9.0
- Change version attributes and semantics. Before: had a _version_
  tuple. After: __version__ is a string, __version_info__ is a tuple.

### v0.8.3
- The break-up-large-sets change in 0.8.2 introduced a bug w.r.t adding
  up retvals (doesn't work if retval is None). Fix that.

### v0.8.2
- Add somewhat of HACK fix for doing p4.opened(), p4.sync() and
  p4.resolve() with a large set of files. The test case is whether 'px
  backout 177241' on the ActiveState Perforce repository works. Before
  this the back would hang on Linux and Mac OS X.

### v0.8.1
- Add px.exe to the distro (and to repo) to fix install on Windows

### v0.8.0
- Move hosting of px/p4lib.py to trentm.com. Tweaks to associated bits
  (README.txt, etc.)
- Fix 'px' usage of os.wait(). (Was this an os.wait() API change?)

### v0.7.2:
- Avoid a possible hang when running commands use "*" in the
  filespec. See test/test_hang.py for details.
- Change _raw output to return unsplit output.

### v0.7.1:
- Add '_raw' option to each P4 command to change the return value to
  be the unprocessed results from running p4.

### v0.7.0:
- [Backward incompatibility] Drop 'optv' method of passing p4 options
  to P4 constructor.  Instead use named keyword args. Also add optional
  keyword args to every P4 command to allow overriding the instances p4
  options for a specific command.  This may break p4lib.P4() usage. To
  quickly convert one may use this pattern: Change usages of:

       p4lib.P4(optv-argument)

  to:

       p4 = p4lib.P4( **p4lib.parseOptv(self.__p4optv) )

### v0.6.8:
- Add interfaces in p4lib.py to 'p4 label', 'p4 labels', 'p4 flush',
  'p4 branch', 'p4 branches'.
- Fix bug in p4lib.py interface to 'p4 have' where files containing
  " - " could not be handled.

### v0.6.7:
- Add interface to 'p4 client' and 'p4 clients' in p4lib.py.
- Fix bugs in 'px genpatch' where opened files without changes or
  non-existant added files could not be handled.

### v0.6.6:
- first public release

