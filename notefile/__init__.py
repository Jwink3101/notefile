__version__ = "0.9.0"
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
SAFE_QUERY = os.environ.get("NOTEFILE_SAFE_QUERY", "true").strip().lower() == "true"

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


def query_help(print_help=True, safe=None):
    if safe is None:
        safe = SAFE_QUERY

    if safe:
        help = """\
Queries:
--------
Queries are single statements where the last line must evaluate to True or False.
They are evaluated by a restricted parser (no eval/exec). 

The following variables are defined:

    data    Dictionary of the note itself.
    notes   == data['notes'] or data[<note_field>] if set. The note text.
    tags    == data['tags']. Set of tags (note, all lower case).
    text    Raw contents (YAML/JSON) of the note.
    filename Path to the file being noted.
    notefile_path Path to the notefile sidecar.

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
    norm_tags    Normalize tags (splits commas, lowercases, strips whitespace)

It also includes the `re` module and `ss = shlex.split`. Imports are not supported.
Attribute access is limited to safe string and dict methods.

Additional supported features include but are not limited to:

- Safe builtins: any, all, len, set, list, tuple, sorted, min, max, sum
- Container literals beyond lists (tuples, sets, dicts)
- Comprehensions (list, set, dict, generator)
- Subscripts and slices (e.g., x[0], x[1:3])
- If-expressions (e.g., a if cond else b)
- Dict method access (get, keys, values, items, copy)
- String method allowlist (e.g., splitlines, removeprefix, removesuffix)

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

Reminder: safe queries are restricted but not fully sandboxed; expensive regex or
large computations can still be costly.

Safe queries are now the default. To enable *unsafe* queries on the CLI, set
NOTEFILE_SAFE_QUERY=false. Or use the Note.unsafe_query(...) APIs.
"""
    else:
        help = """\
Queries:
--------
Queries are single statements where the last line must evaluate to True or False.
They are evaluated as Python (with no sandboxing or sanitizing so DO NOT EVALUATE
UNTRUSTED INPUT). The following variables are defined:

    note    Notefile object including attributes such as 'filename',
            'destnote','hidden', etc. See notefile.Notefile documention.
    data    Dictionary of the note itself (optional convenience).
    notes   == data['notes'] or data[<note_field>] if set. The note text.
    tags    == data['tags']. Set object of tags (note, all lower case).
    text    Raw contents (YAML/JSON) of the note.
    filename Path to the file being noted.
    notefile_path Path to the notefile sidecar.

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
    norm_tags    Normalize tags (splits commas, lowercases, strips whitespace)

It also includes the `re` module and `ss = shlex.split`. More cn be imported with
multiple lines.

WARNING: Unsafe queries are deprecated and will be removed in a future release.
Set NOTEFILE_SAFE_QUERY=true to use safe queries.

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

Reminder: `unsafe_query` is unsafe for untrusted input. `safe_query` is restricted
but not fully sandboxed; expensive regex or large computations can still be costly.
"""
    if print_help:
        print(help)
    return help
