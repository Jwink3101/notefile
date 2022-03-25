__version__ = "2.20220325.0"
__author__ = "Justin Winokur"

import sys, os

if sys.version_info < (3, 8):
    sys.stderr.write("ERROR: Must use Python >= 3.8\n")
    sys.exit(1)

# Env Variables
HIDDEN = os.environ.get("NOTEFILE_HIDDEN", "false",).strip().lower() == "true"
DEBUG = os.environ.get("NOTEFILE_DEBUG", "false",).strip().lower() == "true"
NOTEFIELD = os.environ.get("NOTEFILE_NOTEFIELD", "notes",).strip()
FORMAT = os.environ.get("NOTEFILE_FORMAT", "yaml",).strip().lower()

# Constants
NOTESEXT = ".notes.yaml"
NOHASH = "** not computed **"
DT = 1  # mtime change


def debug(*args, **kwargs):
    if DEBUG:
        kwargs["file"] = sys.stderr
        print("DEBUG:", *args, **kwargs)


def warn(*args, **kwargs):
    kwargs["file"] = sys.stderr
    print("WARNING:", *args, **kwargs)


from .find import find
from .notefile import Notefile, get_filenames


def query_help(print_help=True,):
    help = """\
Queries:
--------
Queries are single expression statements that evaluate to True or False and
based on the note. It is evaluated as Python (with no sandboxing or sanitizing
so do not evaluate untrusted input). The following variables are defined:

    note    Notefile object including attributes such as 'filename',
            'destnote','hidden', etc. See Notefile documention
    data    Dictionary of the note
    notes   == data['notes']. The note text
    tags    == data['tags']. Set of tags (note, all lower case)
    text    Raw YAML of the note

And it includes the following functions:

    grep    performs a match against 'notes'. Respects the flags:
            '--match-expr-case','--fixed-strings','--full-word' automatically but 
            can also be overridden with the respective keyword arguments
    
    g       Aliased to grep
    
    tany    Returns True if that tag is in tags: e.g
                tany('tag1','tag2') <==> any(t in tags for t in ['tag1','tag2'])
    
    tall    Returns true if all args are in tags:
                tall('tag1','tag2') <==> all(t in tags for t in ['tag1','tag2'])
    
    t       aliased to tany
    
It also includes the `re` module and `ss = shlex.split`

Queries can replace search-tags and grep but grep is faster if it can be used since it 
is accelerated by not parsing YAML unless needed.

For example, the following return the same thing:

    $ notefile grep word1 word2 
    $ notefile query "grep('word1') or grep('word2')"    
    $ notefile query "grep('word1','word2')"
    $ notefile query "grep(ss('word1 word2'))" # can use shlex.split (ss) 

However, queries can be much more complex. For example:

    $ notefile query "(grep('word1') or grep('word2')) and not grep('word3')"

Limited multi-line support exists. Multiple lines can be delineated by ';'. 
However, the last line must evaluate the query. Example:

    $ notefile query "tt = ['a','b','c']; all(t in tags for t in tt)"
    
Can also pass STDIN with the expression `-` to make quoting a bit less onerous 
    
    $ notefile query - <<EOF
    > a = t('tag1') and not t('tag2')
    > b = g('expr1') or g('expr2') or not g('expr3')
    > a and b
    > EOF

tany and/or tall could also be used:
    
    $ notefile query "tall('a','b','c')"

Queries are pretty flexible and give a good bit of control but some actions
and queries are still better handled directly in Python.

Reminder: Do not query untrusted input!
"""
    if print_help:
        print(help)
    return help
