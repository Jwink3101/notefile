#!/usr/bin/env python
# coding: utf-8
"""
Synchronize macOS Finder tags with Notefile both ways
"""
import argparse
import subprocess
import os, sys
import sqlite3
import datetime

import notefile

__version__ = "20250726.0"

HISTORY_FILE = os.environ.get(
    "MACOS_NOTEFILE_TAG_SYNC_DB",
    os.path.expanduser("~/.tags_notefile_finder.db"),
)

NOTEFILETAG = "_notefile"

now = datetime.datetime.now().astimezone().isoformat()

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument("--dry-run", action="store_true", help="Dry Run")
parser.add_argument("--path", default=".", help="Specify path. Default '.'")
parser.add_argument(
    "--history-file",
    default=HISTORY_FILE,
    help=f"""
        Specify where to store the history file of tags. 
        
        Can also be specified via the 
        $MACOS_NOTEFILE_TAG_SYNC_DB environment variable.
        
        $MACOS_NOTEFILE_TAG_SYNC_DB is currently 
        {'set to ' if 'MACOS_NOTEFILE_TAG_SYNC_DB' in os.environ else 'not set. Default '}
        {HISTORY_FILE!r}.
        """,
)
parser.add_argument(
    "--map-tags",
    metavar="NOTEFILE,FINDER",
    action="append",
    default=[],
    help="""Specify mappings from notefile to finder tags. Can specify multiple times""",
)

parser.add_argument(
    "--tag-notefiles",
    action=argparse.BooleanOptionalAction,
    default=False,
    help=f"""
        Apply a Finder tag of {NOTEFILETAG!r} if there is a notefile of any kind.
        Default %(default)s.
        """,
)

parser.add_argument("-v", "--version", action="version", version="%(prog)s-" + __version__)

args = parser.parse_args()

args.path = os.path.abspath(args.path)

# Mapping of names
finder2notefile = {}
for val in args.map_tags:
    nf, find = val.split(",")
    finder2notefile[find.lower().strip()] = nf.lower().strip()
notefile2finder = {v: k for k, v in finder2notefile.items()}

# Setup or load the database
#
# See https://stackoverflow.com/a/19343100/3633154 for how we do
# the status table unique


def get_db():
    return sqlite3.connect(os.path.expanduser(args.history_file))


db = get_db()
with db:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS status(
            fullpath STRING,
            tag STRING,           -- always use notefile's as canonical
            UNIQUE(fullpath, tag) -- See reference
        )"""
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS meta(
            key STRING PRIMARY KEY,
            value STRING)
        """
    )

    db.execute(
        """
            INSERT OR IGNORE -- Do not replace. Ignore if already set 
            INTO meta VALUES (?,?)""",
        ("created", now),
    )
    db.execute(
        """
            INSERT OR IGNORE -- Do not replace. Ignore if already set 
            INTO meta VALUES (?,?)""",
        ("version", __version__),
    )


### Get Tags on everything
# Finder
finder = set()
finder_has_note = set()

proc = subprocess.Popen(["tag", "-RG"], stdout=subprocess.PIPE, cwd=args.path)
with proc.stdout:
    for line in proc.stdout:
        line = line.decode("utf8").strip()
        if "\t" not in line:
            continue
        filename, tags = line.split("\t")
        filename = filename.strip()

        filename = os.path.join(args.path, filename)

        tags = tags.strip()
        for tag in tags.split(","):
            tag = tag.lower().strip()
            tag = finder2notefile.get(tag, tag)
            if tag == NOTEFILETAG:
                # Need to use a different set to store
                # for now
                finder_has_note.add((filename, NOTEFILETAG))
            else:
                finder.add((filename, tag))

# Notefile
note = set()
note_has_note = set()

for nf in notefile.find(path=args.path):
    filename = os.path.abspath(os.path.join(args.path, nf.filename))
    note_has_note.add((filename, NOTEFILETAG))

    for tag in nf.data.tags:
        note.add((filename, tag))

# Status
# Status does not need "_has_note" since we don't care.
qpath = args.path
if not qpath.endswith("/"):
    qpath += "/"  # Makes sure a LIKE query catches full dir

status = get_db().execute(
    """
    SELECT * FROM status
    WHERE fullpath LIKE ?""",
    (f"{qpath}%",),
)
status = set(status)


# ## Set Manipulation
#
# `_to_` means things that need to be done. `_is_` means things that hapepend since last status
#
# Algorithm
#
# http://blog.ezyang.com/2012/08/how-offlineimap-works/
# https://unterwaditzer.net/2016/sync-algorithm.html
#
#                             Status
#                          .───────────.
#                       ,─'             '─.
#                    ,─'                   '─.
#                  ,'                         `.
#                 ╱       Stale -- Delete       ╲
#                ╱                               ╲
#               ;                                 :
#               ;                                 :
#              ;                                   :
#              │                                   │
#              │ .───────────.         .───────────.
#             ,─'             '─.   ,─'            ;'─.
#          ,─'  :    Deleted     '─.     Deleted  ;    '─.
#        ,'     :    Finder    ,'   `.    Note    ;       `.
#       ╱        ╲            ╱       ╲          ╱          ╲
#      ╱          ╲          ╱         ╲        ╱            ╲
#     ;            ╲        ;           :      ╱              :
#     ;             `.      ; Unchanged :    ,'               :
#    ;                '─.  ;             :,─'                  :
#    │                   '─│           ,─│                     │
#    │                     │`─────────'  │                     │
#    :                     :             ;                     ;
#     :     New Note        :  Missing  ;      New Finder     ;
#     :                     :    in     ;                     ;
#      ╲                     ╲ Status  ╱                     ╱
#       ╲                     ╲       ╱                     ╱
#        ╲                     ╲     ╱                     ╱
#         `.                    `. ,'                    ,'
# Note      '─.                 ,─'─.                 ,─'    Finder
#              '─.           ,─'     '─.           ,─'
#                 `─────────'           `─────────'

note_to_add, note_to_remove = set(), set()
finder_to_add, finder_to_remove = set(), set()
status_to_add, status_to_remove = set(), set()

# Handle NOTEFILETAG first
if args.tag_notefiles:
    finder_to_remove.update(finder_has_note - note_has_note)
    finder_to_add.update(note_has_note - finder_has_note)

# new notefile
note_is_new = note.difference(finder.union(status))  # note ∖ (finder ⋃ status)

finder_to_add.update(note_is_new)  # actions...
status_to_add.update(note_is_new)

# New finder
finder_is_new = finder.difference(note.union(status))  # finder ∖ (note ⋃ status)

note_to_add.update(finder_is_new)
status_to_add.update(finder_is_new)

# Deleted on notefile
note_is_del = (finder.intersection(status)).difference(note)  # (finder ⋂ status) ∖ note

finder_to_remove.update(note_is_del)
status_to_remove.update(note_is_del)

# Deleted on finder
finder_is_del = (note.intersection(status)).difference(finder)  # (note ⋂ status) ∖ finder

note_to_remove.update(finder_is_del)
status_to_remove.update(finder_is_del)

# Stale (probably deleted on both)
status_is_stale = status.difference(note.union(finder))  # status ∖  (note ⋃ finder)

status_to_remove.update(status_is_stale)

# Missing (New on both or no status)
status_is_missing = (note.intersection(finder)).difference(status)  # (note ⋂ finder) ∖ status

status_to_add.update(status_is_missing)

## Actions

p = "(DRY RUN) " if args.dry_run else ""

# Notefile
for path, tag in note_to_add:
    if not args.dry_run:
        nf = notefile.Notefile(path)
        nf.modify_tags(add=tag)
        nf.save()
    print(f"{p}Notefile Add: {tag} {repr(path)}")

for path, tag in note_to_remove:
    if not args.dry_run:
        nf = notefile.Notefile(path)
        nf.modify_tags(remove=tag)
        nf.save()
    print(f"{p}Notefile Remove: {tag} {repr(path)}")

# finder
for path, tag in finder_to_add:
    if not args.dry_run:
        tag = notefile2finder.get(tag, tag)
        subprocess.check_call(["tag", "--add", tag, path])
    print(f"{p}Finder Add: {tag} {repr(path)}")

for path, tag in finder_to_remove:
    if not args.dry_run:
        tag = notefile2finder.get(tag, tag)
        subprocess.check_call(["tag", "--remove", tag, path])
    print(f"{p}Finder Remove: {tag} {repr(path)}")

# status
if not args.dry_run:
    db = get_db()
    with db:
        db.executemany(
            """
            INSERT OR REPLACE INTO status
            VALUES (?,?)""",
            status_to_add,
        )

        db.executemany(
            """
            DELETE FROM status
            WHERE
                fullpath = ?
            AND
                tag = ?
            """,
            status_to_remove,
        )

        if status_to_remove or status_to_add:
            db.execute(
                """
                INSERT OR REPLACE
                INTO meta 
                VALUES (?,?)""",
                ("modified", now),
            )
