__version__ = "2.20260109.1"
__author__ = "Justin Winokur"

import sys, os

if sys.version_info < (3, 8):
    # Limited by argarse's extend action
    sys.stderr.write("ERROR: Must use Python >= 3.8\n")
    sys.exit(1)

# Env Variables
HIDDEN = os.environ.get("NOTEFILE_HIDDEN", "false").strip().lower() == "true"
SUBDIR = os.environ.get("NOTEFILE_SUBDIR", "false").strip().lower() == "true"

DEBUG = os.environ.get("NOTEFILE_DEBUG", "false").strip().lower() == "true"
NOTEFIELD = os.environ.get("NOTEFILE_NOTEFIELD", "notes").strip()
FORMAT = os.environ.get("NOTEFILE_FORMAT", "yaml").strip().lower()

DISABLE_QUERY = os.environ.get("NOTEFILE_DISABLE_QUERY", "false").lower() == "true"

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


def query_help(print_help=True):
    help = """\
Queries:
--------
Queries are single statements where the last line myst evaluate to True or False. 
It is evaluated as Python (with no sandboxing or sanitizing so DO NOT EVALUATE 
UNTRUSTED INPUT). The following variables are defined:

    note    Notefile object including attributes such as 'filename',
            'destnote','hidden', etc. See notefile.Notefile documention.
    data    Dictionary of the note itself.
    notes   == data['notes'] or data[<note_field>] if set. The note text.
    tags    == data['tags']. Set object of tags (note, all lower case).
    text    Raw contents (YAML/JSON) of the note.

And it includes the following functions:

    grep    performs a match against 'notes'. Respects the flags:
            '--match-expr-case','--fixed-strings','--full-word' automatically but 
            can also be overridden with the respective keyword arguments.
    
    g       Aliased to grep
    
    gall    Essentially grep with match_any = False
    
    gany    Essentially grep with match_any = True
    
    tany    Returns True if that tag is in tags: e.g.
                tany('tag1','tag2') <==> any(t in tags for t in ['tag1','tag2'])
    
    tall    Returns true if all args are in tags: e.g.
                tall('tag1','tag2') <==> all(t in tags for t in ['tag1','tag2'])
    
    t       aliased to tany
    
It also includes the `re` module and `ss = shlex.split`. More cn be imported with
multiple lines.

Queries can replace --tag and grep but grep is faster if it can be used since it 
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

Or even using multiple lines in the shell
    
    $ notefile query "tt = ['a','b','c']
    > all(t in tags for t in tt)"
    
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

Reminder: DO NOT QUERY UNTRUSTED INPUT! There is nothing stopping shell injection!
"""
    if print_help:
        print(help)
    return help
