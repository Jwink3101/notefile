#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hide all notes and tag them.

Must have https://github.com/jdberry/tag installed: brew install tag.

Tries to optimize calls to tag by call it for all files in a directory and
manually travering  the directory (as opposed to using the built in notefile
methods)

Note: Link behavior is inconsistent and therefore all links are disabled
"""

import argparse
import sys
import os
import subprocess
import itertools

import notefile

parser = argparse.ArgumentParser(
    description=__doc__, epilog="", formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument("--batch-size", default=500, type=int, help="Batch size on calling `tag`")
parser.add_argument("-H", "--hide", action="store_true", help="Hide all notes")
parser.add_argument("--tag", default="Red", help="['%(default)s'] Specify the tag to set in Finder")
parser.add_argument("path", default=".", nargs="?", help="Start path")

args = parser.parse_args()


notes = set()
for note in notefile.find_notes(path=args.path, return_note=True, exclude_links=True):
    note = note.filename0
    if note.startswith("./"):
        note = note[2:]
    if not note:
        continue
    notes.add(note)

# TODO: Make this write to a file to prevent lock?
_tagged = subprocess.check_output(["tag", "-R", "-0", "-m", args.tag, args.path])
tagged = set()
for tag in _tagged.split(b"\x00"):
    tag = tag.decode("utf8")
    if tag.startswith("./"):
        tag = tag[2:]
    if not tag:
        continue
    if os.path.islink(tag):
        continue
    tagged.add(tag)


to_tag = notes - tagged
to_untag = tagged - notes


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


for batch in grouper(to_tag, args.batch_size):
    batch = [b for b in batch if b]
    subprocess.call(["tag", "--add", args.tag] + batch)
print(f"Applied tag to {len(to_tag)} items")

for batch in grouper(to_untag, args.batch_size):
    batch = [b for b in batch if b]
    subprocess.call(["tag", "--remove", args.tag] + batch)
print(f"Removed tag from {len(to_untag)} items")

if args.hide:
    c = 0
    for _ in notefile.change_visibility("hide", path=args.path):
        c += 1
    print(f"Hide {c} items")
