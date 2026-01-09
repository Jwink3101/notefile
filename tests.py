#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for notefile.

Tests are run as if from the CLI but run in Python for the sake of test coverage

Generally, with the new design, there is reuse of capabilities given by argument 
groups. So these test commands and argument groups. Once an argument group is tested in 
one (e.g. search), it is not restest for search and find.

"""

import os, io, sys
import shutil
import shlex
import hashlib
import glob
import itertools
import copy
from pathlib import Path
import time
import json
import warnings
import unicodedata
import pickle

import notefile  # this *should* import the local version even if it is installed
import notefile.cli

Notefile = notefile.Notefile

print("version", notefile.__version__)
print("path", notefile.__file__)  # This is just to see that it imported the right now
notefile.DEBUG = False

import pytest

TESTDIR = Path("testdirs").resolve()
TESTDIR.mkdir(parents=True, exist_ok=True)
with (TESTDIR / ".ignore").open("wt") as f:
    pass


class SysExitError(ValueError):
    pass


def call(s, capture=False):
    try:
        if capture:
            try:
                o, e = sys.stdout, sys.stderr
                sys.stdout = io.StringIO()
                sys.stdout.buffer = sys.stdout
                sys.stderr = io.StringIO()
                sys.stderr.buffer = sys.stderr

                notefile.cli.cli(shlex.split(s))

                sys.stdout.flush()
                sys.stderr.flush()

                return sys.stdout.getvalue(), sys.stderr.getvalue()
            finally:
                sys.stdout, sys.stderr = o, e
                sys.stdout.flush()
                sys.stderr.flush()

        return notefile.cli.cli(shlex.split(s))
    except SystemExit:
        raise SysExitError()


class CaptureDebug:
    def __init__(self):
        self.stdout = None
        self.stderr = None

    def __enter__(self):
        self._o, self._e = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stdout.buffer = sys.stdout
        sys.stderr = io.StringIO()
        sys.stderr.buffer = sys.stderr

        self._d = notefile.DEBUG
        notefile.DEBUG = True

        return self

    def __exit__(self, type, value, traceback):
        notefile.DEBUG = self._d

        sys.stdout.flush()
        sys.stderr.flush()

        self.stdout = sys.stdout.getvalue()
        self.stderr = sys.stderr.getvalue()

        sys.stdout, sys.stderr = self._o, self._e
        sys.stdout.flush()
        sys.stderr.flush()


def cleanmkdir(dirpath):
    notefile.DEBUG = False  # Reset this
    try:
        shutil.rmtree(dirpath)
    except:
        pass
    Path(dirpath).mkdir(parents=True)


def writefile(filepath, text="", append=False):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if append:
        with filepath.open(mode="at") as f:
            f.write("\n" + text)
    else:
        filepath.write_text(text)


def readout(out):
    with open(out, "rb") as f:
        lines = f.read().replace(b"\x00", b"\n").decode().split("\n")
    return {l for l in lines if l.strip()}


def readtags(out):
    with open(out) as f:
        tags = notefile.nfyaml.load_yaml(f.read())
    return {tag: (set(files) if isinstance(files, list) else files) for tag, files in tags.items()}


def is_hidden(filename, check_dupe=True):
    """
    returns whether a file exists and is hidden.
    Will assert that (a) the file exists and (b) there
    aren't a hidden and visible if check_dupe
    """
    _, vis, hid = notefile.get_filenames(filename)
    if check_dupe and os.path.exists(vis) and os.path.exists(hid):
        assert False, "Duplicate hidden and visible"

    check_vis = os.path.exists(vis) or os.path.islink(vis)  # broken links still are fine
    check_hid = os.path.exists(hid) or os.path.islink(hid)  # broken links still are fine
    if not (check_hid or check_vis):
        assert False, "Neither file exists"

    return check_hid


def test_mod():
    """
    Test CLI mod
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "mod"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1.")

    call('mod -t tag1 -t tag2 -n"note1" file1.txt')
    note1 = Notefile("file1.txt").read()
    assert note1.data.notes == "note1"
    assert set(note1.data.tags) == {"tag1", "tag2"}

    call('mod -t tag3 -r tag1 -n"more" file1.txt')
    note1 = Notefile("file1.txt").read()
    assert note1.data.notes == "note1\nmore"
    assert set(note1.data.tags) == {"tag3", "tag2"}

    # Test adding via commas
    call('mod -t "tag4,tag 5" -t tag6,tag7 -r "tag2, tag3" file1.txt')
    note1 = Notefile("file1.txt").read()
    assert set(note1.data.tags) == {"tag 5", "tag4", "tag6", "tag7"}
    note1.data.tags = "tag3", "tag2"  # Reset
    note1.write()

    call('mod --replace --note "new" file1.txt')
    note1 = Notefile("file1.txt").read()
    assert note1.data.notes == "new"

    # Monkey patch stdin
    try:
        stdin0 = sys.stdin
        import io

        sys.stdin = io.StringIO("stdin str")
        call('mod -s -n"worked?" file1.txt')
    finally:
        sys.stdin = stdin0
    note1 = Notefile("file1.txt").read()
    assert note1.data.notes == "new\nstdin str\nworked?"

    # This will run through the code for edit but with a special flag just for testing
    try:
        # Regular
        notefile.notefile._TESTEDIT = "test note"
        note1.interactive_edit()
        assert note1.data.notes == "test note"

        # full
        note2 = copy.deepcopy(note1)
        note2.data.notes = "mod full"
        note2.data.tags = ["tag1"]
        note2.data.other = {"other": "data"}

        notefile.notefile._TESTEDIT = note2.writes()
        del note2  # not needed but to make sure I do not mess up

        note1.interactive_edit(full=True)
        assert note1.data.other == {"other": "data"}
        assert set(note1.data.tags) == {"tag1"}
        assert note1.data.notes == "mod full"
    finally:
        notefile.notefile._TESTEDIT = False

    os.chdir(TESTDIR)


def test_create_opts():
    """
    Test "new" options
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "create"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    ## --hidden and --visible
    writefile("file1.txt", "file1.")
    writefile("file2.txt", "file2..")
    writefile("file3.txt", "file3...")

    call('mod -n "note" file1.txt')
    call('mod -n "note" -V file2.txt')
    call('mod -n "note" -H file3.txt')
    assert os.path.exists("file1.txt.notes.yaml") and not os.path.exists(".file1.txt.notes.yaml")
    assert os.path.exists("file2.txt.notes.yaml") and not os.path.exists(".file2.txt.notes.yaml")
    assert os.path.exists(".file3.txt.notes.yaml") and not os.path.exists("file3.txt.notes.yaml")

    ## --no-hash
    writefile("file4.txt", "file4....")
    call('mod -n "note" file4.txt --no-hash')
    note3 = Notefile("file3.txt").read()
    note4 = Notefile("file4.txt").read()
    assert "sha256" in note3.data and "sha256" not in note4.data

    ## --no-refresh
    writefile("file5.txt", "file5.....")
    call('mod -n "note" file5.txt')
    h1 = Notefile("file5.txt").read().data.sha256

    writefile("file5.txt", "a", append=True)
    call('mod -n "note2" file5.txt')
    h2 = Notefile("file5.txt").read().data.sha256
    assert h1 != h2

    writefile("file5.txt", "a", append=True)
    call('mod -n "note3" file5.txt --no-refresh')
    h3 = Notefile("file5.txt").read().data.sha256
    assert h2 == h3

    ## Refresh after --no-hash
    writefile("file6.txt", "file6......")
    call('mod -n "note" file6.txt --no-hash')
    assert "sha256" not in Notefile("file6.txt").read().data

    call('mod -n "note2" file6.txt')
    assert "sha256" not in Notefile("file6.txt").read().data

    # Modifying the file SHOULD make it compute the hash unless --no-refresh is set again
    writefile("file6.txt", "line", append=True)
    call('mod -n "note3" file6.txt --no-refresh')
    assert "sha256" not in Notefile("file6.txt").read().data

    writefile("file6.txt", "line3", append=True)
    call('mod -n "note4" file6.txt')
    assert "sha256" in Notefile("file6.txt").read().data  # refreshed

    ## Link mode
    # Visible
    writefile("file7.txt", "file7.......")
    writefile("file8.txt", "file8........")
    writefile("file9.txt", "file9.........")
    os.symlink("file7.txt", "link7.txt")
    os.symlink("file8.txt", "link8.txt")
    os.symlink("file9.txt", "link9.txt")

    call("mod -t link link7.txt --link both")
    call("mod -t link link8.txt --link symlink")
    call("mod -t link link9.txt --link source")

    assert os.path.exists("link7.txt.notes.yaml") and os.path.exists("file7.txt.notes.yaml")
    assert os.path.exists("link8.txt.notes.yaml") and not os.path.exists("file8.txt.notes.yaml")
    assert not os.path.exists("link9.txt.notes.yaml") and os.path.exists("file9.txt.notes.yaml")

    # Hidden
    writefile("file10.txt", "file10..........")
    writefile("file11.txt", "file11...........")
    writefile("file12.txt", "file12............")
    os.symlink("file10.txt", "link10.txt")
    os.symlink("file11.txt", "link11.txt")
    os.symlink("file12.txt", "link12.txt")

    call("mod -t link link10.txt --hidden --link both")
    call("mod -t link link11.txt --hidden --link symlink")
    call("mod -t link link12.txt --hidden --link source")

    assert os.path.exists(".link10.txt.notes.yaml") and os.path.exists(".file10.txt.notes.yaml")
    assert os.path.exists(".link11.txt.notes.yaml") and not os.path.exists(".file11.txt.notes.yaml")
    assert not os.path.exists(".link12.txt.notes.yaml") and os.path.exists(".file12.txt.notes.yaml")

    # Visible on existing hidden
    os.symlink("file10.txt", "link10-V.txt")
    os.symlink("file11.txt", "link11-V.txt")
    os.symlink("file12.txt", "link12-V.txt")

    call("mod -t link2 link10-V.txt --visible --link both")
    call("mod -t link2 link11-V.txt --visible --link symlink")
    call("mod -t link2 link12-V.txt --visible --link source")

    assert os.path.exists("link10-V.txt.notes.yaml") and os.path.exists(".file10.txt.notes.yaml")
    assert os.path.exists("link11-V.txt.notes.yaml") and not os.path.exists(
        ".file11.txt.notes.yaml"
    )
    assert not os.path.exists("link12-V.txt.notes.yaml") and os.path.exists(
        ".file12.txt.notes.yaml"
    )

    assert (
        Notefile("link10-V.txt").read().data.tags
        == Notefile("link10.txt").read().data.tags
        == Notefile("file10.txt").read().data.tags
    )
    assert Notefile("link11-V.txt").read().data.tags == ["link2"]
    assert Notefile("link11.txt").read().data.tags == ["link"]
    assert Notefile("file11.txt").read().data.tags == []
    assert (
        Notefile("link12-V.txt").read().data.tags
        == Notefile("link12.txt").read().data.tags
        == Notefile("file12.txt").read().data.tags
    )

    ## --format and rewrite-format
    writefile("file13.txt", "file13.............")

    call("mod -t note file13.txt --format json")
    assert Notefile("file13.txt").read().format == "json"

    call("mod -t note2 file13.txt --format yaml")  # should NOT change format
    assert Notefile("file13.txt").read().format == "json"

    call("mod -t note3 file13.txt --format yaml --rewrite-format")  # should now change format
    assert Notefile("file13.txt").read().format == "yaml"

    os.chdir(TESTDIR)


def test_copy():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "copy"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1.")
    writefile("file2.txt", "file2..")
    writefile("file3.txt", "file3...")

    call('mod -t tag1 -n"this note" file1.txt')
    call("copy -H file1.txt file2.txt file3.txt")  # also test -H again

    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    note3 = Notefile("file3.txt").read()
    for key in set(note1.data).difference(notefile.notefile.METADATA):
        assert note1.data[key] == note2.data[key] == note3.data[key], f"failed {key}"
    assert note2.is_hidden == note3.is_hidden == True

    try:
        call("copy file1.txt file2.txt --debug")  # --debug to get the error
        assert False
    except ValueError:
        pass

    os.chdir(TESTDIR)


def test_replace():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "replace"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    ## Regular
    writefile("file1.txt", "file1.")
    writefile("file2.txt", "file2..")
    writefile("file3.txt", "file3...")
    writefile("file4.txt", "file4....")

    call('mod -t tag1 -t tagshared -n"note file 1" file1.txt')
    call('mod -t tag2 -t tagshared -n"note FILE 2" file2.txt')
    call('mod -t tag3 -t tagshared -n"note FiLe 3" file3.txt')
    call('mod -t tag4 -t tagshared -n"NOTE FiLe 4" file4.txt')

    call("replace file1.txt file2.txt")
    call("replace file1.txt file3.txt --field tags")
    call("replace file1.txt file4.txt --all-fields")

    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    note3 = Notefile("file3.txt").read()
    note4 = Notefile("file4.txt").read()

    assert note1.data.notes == note2.data.notes
    assert note1.data.tags != note2.data.tags

    assert note1.data.notes != note3.data.notes
    assert note1.data.tags == note3.data.tags

    assert note1.data.notes == note4.data.notes
    assert note1.data.tags == note4.data.tags

    ## Appends
    writefile("file5.txt", "file5.....")

    call("replace file1.txt file5.txt")
    call("replace file3.txt file5.txt --append")
    note5 = Notefile("file5.txt").read()

    assert note5.data.notes == "note file 1\nnote FiLe 3"  # appended notes

    call("mod -t newtag file5.txt")
    call("replace file1.txt file5.txt --field tags --append")
    note5 = Notefile("file5.txt").read()
    assert set(note5.data.tags) == {"newtag", "tag1", "tagshared"}  # kep newtag

    ## Appends on non-text fields
    writefile("file6.txt", "file6......")
    writefile("file7.txt", "file7.......")
    note6 = Notefile("file6.txt").read()

    note6.data.newstring = "this is a string field"
    note6.data.newdict = {"this is": "a dict"}
    note6.data.newlist = ["this is", "a", "list"]
    note6.write()

    call(
        "replace file6.txt file7.txt --all-fields --append"
    )  # This will work since new(dict/list() doesn't yet exists_action()
    note7 = Notefile("file7.txt").read()
    for key in {
        "newdict",
        "newstring",
        "notes",
        "newlist",
        "tags",
    }:  # set(note6.data).difference(notefile.notefile.METADATA)
        assert note6.data[key] == note7.data[key], f"failed {key}"

    call("replace file6.txt file7.txt --field newstring --append")
    note7 = Notefile("file7.txt").read()
    assert note7.data.newstring == "this is a string field\nthis is a string field"

    try:
        call("replace file6.txt file7.txt --field newdict --append --debug")
        assert False
    except TypeError:
        pass

    try:
        call("replace file6.txt file7.txt --field newlist --append --debug")
        assert False
    except TypeError:
        pass

    # Non-existing fields
    call(
        "replace file1.txt file7.txt --field newlist --append"
    )  # even though newlist is on file7, it isn't on 1 so ignore
    call("replace file1.txt file7.txt --field allnew --append")  # Not on either. Do nothing

    os.chdir(TESTDIR)


@pytest.mark.parametrize("vis", (True, False))
def test_change_viz_and_format(vis):
    """
    Test changing viz and also formats. If vis will keep the legacy "vis" commands
    """
    vis = "vis" if vis else ""
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "formats"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    # Viz first
    writefile("file1.txt", "file1.")
    writefile("file2.txt", "file2..")
    call("mod -V -t tag -n note file1.txt")
    call("mod -H -t tag -n note file2.txt")

    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert not note1.is_hidden and note2.is_hidden

    # verify the built-in settings
    assert os.path.exists("file1.txt.notes.yaml")
    assert not os.path.exists(".file1.txt.notes.yaml")
    assert os.path.exists(".file2.txt.notes.yaml")
    assert not os.path.exists("file2.txt.notes.yaml")

    # Make sure they do not change
    call(f"{vis} show file1.txt")  # already vis
    call(f"{vis} hide file2.txt")  # already hidden
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert not note1.is_hidden and note2.is_hidden

    # Change one
    call(f"{vis} show file2.txt")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert not note1.is_hidden and not note2.is_hidden

    # Change both
    call(f"{vis} hide")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.is_hidden and note2.is_hidden

    call(f"{vis} show --dry-run")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.is_hidden and note2.is_hidden

    shutil.copy(".file1.txt.notes.yaml", "file1.txt.notes.yaml")
    with pytest.raises(notefile.notefile.MultipleNotesError):
        call("vis --debug show file1.txt", capture=True)
    os.unlink("file1.txt.notes.yaml")

    ## JSON vs YAML
    # Verify the mode.
    try:
        with open(note1.destnote) as f:
            json.load(f)
        assert False
    except json.decoder.JSONDecodeError:
        assert True  # Not JSON
    try:
        with open(note2.destnote) as f:
            json.load(f)
        assert False
    except json.decoder.JSONDecodeError:
        assert True  # Not JSON
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.format == note2.format == "yaml"

    call("format json file1.txt")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.format == "json" and note2.format == "yaml"
    try:
        with open(note1.destnote) as f:
            json.load(f)
        assert True
    except json.decoder.JSONDecodeError:
        assert False  # Not JSON

    call("format json")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.format == note2.format == "json"

    call("format yaml --dry-run")
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert note1.format == note2.format == "json"

    os.chdir(TESTDIR)


def test_change_tag():
    """
    Test changing viz and also formats
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "change-tag"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    # Viz first
    writefile("file1.txt", "file1.")
    writefile("file2.txt", "file2..")
    call("mod -t tag -t tag1 file1.txt")
    call("mod -t tag -t tag2 file2.txt")

    call("change-tag tag1 tag11 --dry-run -o tmp")

    assert Path("tmp").read_text() == "# DRY RUN\nfile1.txt\n"
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert set(note1.data.tags) == {"tag", "tag1"}
    assert set(note2.data.tags) == {"tag", "tag2"}

    call("change-tag tag1 tag11 -o tmp -p file2.txt")

    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert set(note1.data.tags) == {"tag", "tag1"}
    assert set(note2.data.tags) == {"tag", "tag2"}

    call(r"change-tag tag1 tag11 tag\ 1 -o tmp")

    assert Path("tmp").read_text() == "file1.txt\n"
    note1 = Notefile("file1.txt").read()
    note2 = Notefile("file2.txt").read()
    assert set(note1.data.tags) == {"tag", "tag11", "tag 1"}
    assert set(note2.data.tags) == {"tag", "tag2"}

    os.chdir(TESTDIR)


def test_find_exclusions():
    """
    Test all of the find exclusions that play into search, grep, query, and tags
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "find"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    files = {
        "file1.txt",
        "sub/file2.txt",
        "sub/file3.exc",
        "sub/exd/file4.txt",
        "exd/file5.txt",
        "dup/file1.txt",
        "endxd",
    }

    for i, file in enumerate(files):
        file = Path(file)
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_text(f"{file}")
        note = Notefile(file).read()
        note.add_note(f"this is a note for {file}")
        note.modify_tags(add="tag1").modify_tags((f"tag_{i}", "tag2"))
        note.write()

    assert {n.filename for n in notefile.find()} == files

    call("find -o tmp")
    assert readout("tmp") == files

    # Single exclusion
    f = {
        "dup/file1.txt",
        "endxd",
        "exd/file5.txt",
        "file1.txt",
        "sub/exd/file4.txt",
        "sub/file2.txt",
    }
    assert {n.filename for n in notefile.find(excludes="*.exc")} == f

    assert {n.filename for n in notefile.find(path="sub", excludes="*.exc")} == {
        "sub/exd/file4.txt",
        "sub/file2.txt",
    }
    assert {n.filename for n in notefile.find(path=Path("sub"), excludes="*.exc")} == {
        "sub/exd/file4.txt",
        "sub/file2.txt",
    }

    call('find --exclude "*.exc" -o tmp')
    assert readout("tmp") == f

    # Single exclusion with dir
    call('find --exclude "*xd" -o tmp')
    assert readout("tmp") == {
        "sub/file3.exc",
        "file1.txt",
        "sub/file2.txt",
        "dup/file1.txt",
    }

    call('find --exclude "*xd/" -o tmp')
    assert readout("tmp") == {
        "endxd",
        "sub/file3.exc",
        "file1.txt",
        "sub/file2.txt",
        "dup/file1.txt",
    }

    # Match case
    call('find --exclude "*.TXT" -o tmp')
    assert readout("tmp") == {"sub/file3.exc", "endxd"}

    call('find --exclude "*.TXT" -o tmp --match-exclude-case ')
    assert readout("tmp") == files

    # Test path
    call("find -p sub -o tmp")
    assert readout("tmp") == {"sub/file3.exc", "sub/file2.txt", "sub/exd/file4.txt"}

    # max-depth
    call("find --max-depth 0 -o tmp")
    assert readout("tmp") == {"endxd", "file1.txt"}

    # test links. Add one now
    os.symlink("dup/file1.txt", "link1.lnk")
    Notefile("link1.lnk").read().write()  # Make the links

    call('find --exclude "*.txt" -o tmp')
    assert readout("tmp") == {"link1.lnk", "endxd", "sub/file3.exc"}

    call('find --exclude "*.txt" -o tmp')
    assert readout("tmp") == {"link1.lnk", "endxd", "sub/file3.exc"}

    call('find --exclude "*.txt" --exclude-links -o tmp')
    assert readout("tmp") == {"endxd", "sub/file3.exc"}

    os.chdir(TESTDIR)


def test_outputs_export():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "outputs"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    files = {"file1.txt", "sub/file1.txt", "sub2/file3.exc"}

    for i, file in enumerate(sorted(files)):
        file = Path(file)
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_text(f"{file}")
        note = Notefile(file).read()
        note.add_note(f"this is a note for {file}")
        note.modify_tags(add=("tag1", f"tag_{i}"))
        note.write()

    ## Test outputs
    call("find -0 -o tmp")
    with open("tmp", "rb") as f:
        dat = f.read()
        assert b"\n" not in dat
        assert b"\x00" in dat

    call("find --tag-mode -o tmp")
    assert set(readtags("tmp")) == {"tag_1", "tag1", "tag_0", "tag_2"}
    # Other tag modes like --tag-counts and --tag-count-order are in test_search()

    ## export
    for format in ["yaml", "json", "jsonl"]:
        call(f"export -o tmp --export-format {format}")
        if format == "yaml":
            with open("tmp") as f:
                export = notefile.nfyaml.load_yaml(f.read())
        elif format == "json":
            # Explicitly check that json can load it
            with open("tmp") as f:
                export = json.load(f)
            assert export.pop("__comment", False)
        else:
            with open("tmp") as fp:
                export = [json.loads(line) for line in fp]
            comment = export.pop(0)
            assert comment.pop("__comment", False)

            export0, export = export, {}
            export.update(comment)
            export["notes"] = {}
            for line in export0:
                export["notes"][line.pop("__filename")] = line

    assert set(export.keys()) == {"notefile version", "notes", "description", "time"}
    assert set(export["notes"]) == {"sub/file1.txt", "sub2/file3.exc", "file1.txt"}
    tags = set()
    for data in export["notes"].values():
        tags.update(data["tags"])
    assert tags == {"tag1", "tag_0", "tag_2", "tag_1"}

    ## symlinks
    call("find --symlink links")
    links = {}
    for link in os.listdir("links"):
        links[link] = os.readlink(f"links/{link}")
    assert links == {
        "file1.txt": "../file1.txt",
        "file1.1.txt": "../sub/file1.txt",
        "file3.exc": "../sub2/file3.exc",
    }

    # Symlinks with tags
    shutil.rmtree("links")
    o, e = call("find --tag-mode --symlink links --debug", capture=True)
    # There is a duplicate. Check it works right
    assert e == "WARNING: links/tag1/file1.txt exists. Changing to links/tag1/file1.1.txt\n"

    # Check them. Note that the ordering may not be deterministic of the repeat so handle
    # that properly
    links = {str(p): os.readlink(p) for p in Path("links").rglob("*") if p.is_file()}
    file1 = links.pop("links/tag1/file1.txt")  # Will error if not in there
    file1p1 = links.pop("links/tag1/file1.1.txt")
    assert {file1, file1p1} == {
        "../../sub/file1.txt",
        "../../file1.txt",
    }  # use set to ignore order

    assert links == {
        "links/tag1/file3.exc": "../../sub2/file3.exc",
        "links/tag_0/file1.txt": "../../file1.txt",
        "links/tag_1/file1.txt": "../../sub/file1.txt",
        "links/tag_2/file3.exc": "../../sub2/file3.exc",
    }

    os.chdir(dirpath)


def test_search():
    """
    Test the different queries and searches. No need to test exclusions, etc
    as they are tested as part of find
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "search"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1")
    call('mod file1.txt -t xcommon -t file1 -n"match me or you"')

    writefile("file2.txt", "file2")
    call('mod file2.txt -t xcommon -t other -n"match you"')

    writefile("file3.txt", "file2")
    call('mod file3.txt -t xcommon -t third -t other -n"what about me"')

    # Test a few greps and also query and search
    call("grep match -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt"}
    call("search --grep match -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt"}
    call("query 'g(\"match\")' -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt"}
    call("search --query 'g(\"match\")' -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt"}

    # Regex
    call('grep "wh.*t" -o tmp')
    assert readout("tmp") == {"file3.txt"}

    # Multiple
    call("grep me you -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt", "file3.txt"}

    call("grep me you --all -o tmp")
    assert readout("tmp") == {"file1.txt"}

    ## --full-note tests. Look for 'xcommon' since it'll just be in the tags
    call("grep xcommon -o tmpnew")
    assert not os.path.exists("tmpnew")  # Make sure it's not there
    call("grep --full-note xcommon -o tmp")
    assert readout("tmp") == {"file1.txt", "file2.txt", "file3.txt"}
    call("""query --full-note "g('xcommon')" -o tmp""")
    assert readout("tmp") == {"file1.txt", "file2.txt", "file3.txt"}
    call("""query "'xcommon' in text" -o tmp""")
    assert readout("tmp") == {"file1.txt", "file2.txt", "file3.txt"}

    ## Test grep with regex
    writefile("file4.txt", "wt", "FILE 4")
    writefile("file5.txt", "wt", "FILE 5")
    writefile("file6.txt", "wt", "FILE 6")
    writefile("file7.txt", "wt", "FILE 7")

    call('mod file4.txt -n "this is a te.*st"')
    call('mod file5.txt -n "This is a teblablabast"')
    call('mod file6.txt -n "These are their words"')
    call('mod file7.txt -n "these are the words"')

    call('grep -o tmp "te.*st"')
    assert readout("tmp") == {"file4.txt", "file5.txt"}

    call("""search -o tmp --query 'g("te.*st")'""")
    assert readout("tmp") == {"file4.txt", "file5.txt"}

    call('grep -o tmp --fixed-strings "te.*st"')
    assert readout("tmp") == {"file4.txt"}

    call("""query -o tmp --fixed-strings 'g("te.*st")' """)  # Make sure the flags work in query
    assert readout("tmp") == {"file4.txt"}

    # Or passing kwargs including override
    call("""query -o tmp 'g("te.*st",fixed_strings=True)'""")
    assert readout("tmp") == {"file4.txt"}

    call("""query -o tmp --fixed-strings 'g("te.*st",fixed_strings=False)' """)
    assert readout("tmp") == {"file4.txt", "file5.txt"}

    call("grep -o tmp the")
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    call("grep -o tmp --full-word the")
    assert readout("tmp") == {"file7.txt"}

    call("query -o tmp --full-word 'g(\"the\")' ")
    assert readout("tmp") == {"file7.txt"}

    # Multiple in query
    # any
    call("""query "g('the','words')" -o tmp""")  # default
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    call("""query "g('the','words')" --full-word -o tmp""")  # Baseline for below
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    call("""query "g('the','words',match_any=True)" --full-word --all -o tmp""")  # kw overides CLI
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    call("""query "gany('the','words')" --full-word --all -o tmp""")  # gany overides CLI
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    # all
    call("""query "g('the','words')" --all --full-word -o tmp""")  # cli --all
    assert readout("tmp") == {"file7.txt"}

    call("""query "g('the','words',match_any=False)" --full-word -o tmp""")  # kw all
    assert readout("tmp") == {"file7.txt"}

    call("""query "gall('the','words')" --full-word -o tmp""")  # implied with gall
    assert readout("tmp") == {"file7.txt"}

    call(
        """query "gall('the','words',match_any=True)" --full-word -o tmp"""
    )  # implied with gall but again overwritten with kw
    assert readout("tmp") == {"file6.txt", "file7.txt"}

    ## Tags
    call("tags -o tmp")
    assert readtags("tmp") == {
        "xcommon": {"file2.txt", "file1.txt", "file3.txt"},
        "file1": {"file1.txt"},
        "other": {"file2.txt", "file3.txt"},
        "third": {"file3.txt"},
    }

    call("search --tag-mode -o tmp1")  # search tag mode calls
    call("find --tag-mode -o tmp2")
    assert readtags("tmp") == readtags("tmp1") == readtags("tmp2")

    call("tags third other -o tmp")
    call("""query "t('third') or t('other')" --tag-mode -o tmp2""")
    call("""search --query "t('third')" --query "t('other')" --tag-mode -o tmp3""")
    assert (
        readtags("tmp")
        == readtags("tmp2")
        == readtags("tmp3")
        == {
            "xcommon": {"file2.txt", "file3.txt"},
            "other": {"file2.txt", "file3.txt"},
            "third": {"file3.txt"},
        }
    )

    call("""query "t('third') or t('other')" -o tmp""")
    assert readout("tmp") == {"file2.txt", "file3.txt"}

    call("tags --tag-counts -o tmp")
    readtags("tmp") == {"xcommon": 3, "file1": 1, "other": 2, "third": 1}

    # Multiple (all) with some mix and match
    call("tags --tag-all third other -o tmp")
    call("""query "t('third') and t('other')" --tag-mode -o tmp2""")
    call("""search --query "t('third')" --query "t('other')" --all --tag-mode -o tmp3""")
    call("""search --tag other --query 't("third")' --all --tag-mode -o tmp4""")
    assert (
        readtags("tmp")
        == readtags("tmp2")
        == readtags("tmp3")
        == {"xcommon": {"file3.txt"}, "other": {"file3.txt"}, "third": {"file3.txt"}}
    )

    # Ordering
    call("tags -o tmp")
    assert list(readtags("tmp")) == ["file1", "other", "third", "xcommon"]

    call("tags --tag-count-order -o tmp")
    call("tags --tag-count-order --tag-counts -o tmp2")
    call("""search --query "t('third')" --query "t('other')" --all --tag-mode -o tmp3""")
    assert set(readtags("tmp")) == set(readtags("tmp2")) == {"xcommon", "other", "file1", "third"}

    ## Errors
    try:
        call('''query "asdf"''')
        assert False
    except SysExitError:
        assert True

    o, e = call('''query -e "asdf"''', capture=True)
    assert "WARNING: Query Error" in e
    assert not o

    os.chdir(TESTDIR)


def test_links():
    """
    Test the link modes, absolute and relative, and to different depth
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "links"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    ## Link to deeper with both mode
    writefile("sub/dir/file1", "file 1")
    os.symlink("sub/dir/file1", "link1r")

    writefile("sub/dir/file2", "file 2")
    os.symlink(dirpath / "sub/dir/file2", "link2a")
    assert os.path.exists("link1r") and os.path.exists("link2a")

    call("mod -t link1 -n file1 link1r --link both")
    call("mod -t link2 -n file2 link2a --link both")

    assert os.readlink("link1r.notes.yaml") == "sub/dir/file1.notes.yaml"
    assert os.readlink("link2a.notes.yaml") == str(dirpath / "sub/dir/file2.notes.yaml")

    note1f = Notefile("sub/dir/file1").read()
    note1l = Notefile("link1r").read()
    assert note1l.data == note1f.data

    ## Link backwards relative only. both mode
    writefile("file3", "file 3")
    os.symlink("../../file3", "sub/dir/link3")
    assert os.path.exists("sub/dir/link3")

    call("mod -t link --link both sub/dir/link3")
    assert os.path.exists("sub/dir/link3.notes.yaml")
    assert os.readlink("sub/dir/link3.notes.yaml") == "../../file3.notes.yaml"

    ## Different modes on new
    writefile("file4", "file 4")
    os.symlink("file4", "link4")
    writefile("file5", "file 5")
    os.symlink("file5", "link5")
    writefile("file6", "file 6")
    os.symlink("file6", "link6")

    call("mod -t link link4 --link both")
    call("mod -t link link5 --link source")
    call("mod -t link link6 --link symlink")

    assert os.path.exists("file4.notes.yaml") and os.path.exists("link4.notes.yaml")
    assert os.path.exists("file5.notes.yaml") and not os.path.exists("link5.notes.yaml")
    assert not os.path.exists("file6.notes.yaml") and os.path.exists("link6.notes.yaml")

    ## Linking existing notes
    writefile("file7", "file 7")
    os.symlink("file7", "link7")
    call("mod -t link file7")  # on file
    assert os.path.exists("file7.notes.yaml") and not os.path.exists("link7.notes.yaml")
    call("mod -t other link7")  # on link
    assert os.path.exists("file7.notes.yaml") and os.path.exists("link7.notes.yaml")
    assert set(Notefile("file7").read().data.tags) == {"link", "other"}

    writefile("file8", "file 8")
    os.symlink("file8", "link8")
    call("mod -t link file8")  # on file
    assert os.path.exists("file8.notes.yaml") and not os.path.exists("link8.notes.yaml")
    call("mod -t other link8 --link source")  # on link
    assert os.path.exists("file8.notes.yaml") and not os.path.exists("link8.notes.yaml")
    assert set(Notefile("file8").read().data.tags) == {"link", "other"}

    # Read it without 'source' mode
    link8 = Notefile("link8").read()
    assert not os.path.exists("link8.notes.yaml")  # Doesn't yet exit
    link8.write()
    assert os.path.exists("link8.notes.yaml")  # Now it does

    writefile("file9", "file 9")
    os.symlink("file9", "link9")
    call("mod -t link file9")  # on file
    assert os.path.exists("file9.notes.yaml") and not os.path.exists("link9.notes.yaml")
    call("mod -t other link9 --link symlink")  # on link
    assert os.path.exists("file9.notes.yaml") and os.path.exists("link9.notes.yaml")
    assert set(Notefile("file9").read().data.tags) == {"link"}
    assert set(Notefile("link9", link="symlink").read().data.tags) == {"other"}

    # create a new note without setting the mode
    _, e = call("mod -t new link9", capture=True)
    assert e.startswith("WARNING: Linked file")

    ## Create with a different mode from existing
    writefile("file10", "file 10")
    os.symlink("file10", "link10")
    call("mod -t tag file10")
    call("mod -t other link10 -H")
    assert os.path.exists("file10.notes.yaml") and not os.path.exists(".file10.notes.yaml")
    assert os.path.exists(".link10.notes.yaml") and not os.path.exists("link10.notes.yaml")

    file10 = Notefile("file10").read()
    link10 = Notefile("link10").read()
    assert link10.is_hidden0 and not file10.is_hidden

    ## Break by vis
    call("vis hide file10")
    assert os.path.exists(".file10.notes.yaml") and not os.path.exists("file10.notes.yaml")
    assert not os.path.exists(".link10.notes.yaml") and not os.path.exists(
        "link10.notes.yaml"
    )  # exists fails for broken
    Notefile("link10").read().write()  # reapir by writing
    assert os.path.exists(".link10.notes.yaml") and not os.path.exists("link10.notes.yaml")  # Fixed

    call("vis show file10")
    assert os.path.exists("file10.notes.yaml") and not os.path.exists(".file10.notes.yaml")
    assert not os.path.exists(".link10.notes.yaml") and not os.path.exists(
        "link10.notes.yaml"
    )  # exists fails for broken
    call("repair link10")  # repair function
    assert os.path.exists(".link10.notes.yaml") and not os.path.exists("link10.notes.yaml")  # Fixed

    ## Broken Links
    writefile("file11", "file 11")
    os.symlink("broke11", "link11")
    _, e = call("mod -t d link11", capture=True)
    assert (
        "WARNING: 'link11' is a broken link to 'broke11'" in e
        and "WARNING: File 'broke11' is orphaned or link is broken" in e
    )
    assert os.readlink("link11.notes.yaml") == "broke11.notes.yaml"  # stil link to it

    os.chdir(TESTDIR)


def test_unicode_spaces():
    """
    Test unicode, etc
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "unicode"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file 1", "file 11")
    call(r'mod -t "t°gs" file\ 1')

    writefile("s°b dir/spüd.txt", "file2")
    call("mod -n hi 's°b dir/spüd.txt' ")

    os.symlink("s°b dir/spüd.txt", " leading.txt")
    call('mod -t tttt " leading.txt"')

    call('find -o "tmp"')
    call("find -0o tmp0")

    un = lambda f: unicodedata.normalize("NFC", f)

    tmp = {un(f) for f in readout("tmp")}
    tmp0 = {un(f) for f in readout("tmp0")}
    truth = {un(f) for f in {"s°b dir/spüd.txt", "file 1", " leading.txt"}}
    assert tmp == tmp0 == truth

    call("find --tag-mode -o tmp")

    data = {un(k): {un(_v) for _v in v} for k, v in readtags("tmp").items()}
    truth = {
        un(k): {un(_v) for _v in v}
        for k, v in {
            "tttt": {" leading.txt", "s°b dir/spüd.txt"},
            "t°gs": {"file 1"},
        }.items()
    }

    assert data == truth

    os.chdir(TESTDIR)


def test_notepath():
    """
    Test unicode, etc
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "notepath"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt")
    writefile("sub/file2.txt")
    writefile("file3.txt")

    call("mod -t note file1.txt")
    call("mod -t tag sub/file2.txt --hidden")

    # These shouldn't be affected by vis or hide
    o0, _ = call("note-path file1.txt sub/file2.txt", capture=True)
    oH, _ = call("note-path file1.txt sub/file2.txt -H", capture=True)
    oV, _ = call("note-path file1.txt sub/file2.txt -V", capture=True)
    assert o0 == oH == oV == "file1.txt.notes.yaml\nsub/.file2.txt.notes.yaml\n"

    # These *do* care. file3.txt exisst but no note.
    oV, _ = call("note-path file3.txt ss/nofile.no -V", capture=True)
    oH, _ = call("note-path file3.txt ss/nofile.no -H", capture=True)
    assert oV == "file3.txt.notes.yaml\nss/nofile.no.notes.yaml\n"
    assert oH == ".file3.txt.notes.yaml\nss/.nofile.no.notes.yaml\n"

    os.chdir(TESTDIR)


def test_metadata_repair():
    """
    Test unicode, etc
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "metadata-repair"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    meta = "mtime", "sha256", "filesize"

    writefile("file1.txt", "a")
    call("mod -t tag file1.txt")
    note = Notefile("file1.txt").read()
    data0 = note.data.copy()

    # Add to it
    writefile("file1.txt", "a", append=True)
    assert data0 == Notefile("file1.txt").read().data
    assert note.repair_metadata()
    note.write()
    assert data0 != note.read().data

    data0 = Notefile("file1.txt").read().data
    writefile("file1.txt", "a", append=True)
    assert data0 == Notefile("file1.txt").read().data
    call("repair-metadata file1.txt")
    assert data0 != Notefile("file1.txt").read().data

    data0 = Notefile("file1.txt").read().data
    writefile("file1.txt", "a", append=True)
    assert data0 == Notefile("file1.txt").read().data
    o, _ = call("repair-metadata", capture=True)  # do not specify
    assert data0 != Notefile("file1.txt").read().data
    assert o == "repaired: file1.txt\n"

    data0 = Notefile("file1.txt").read().data
    writefile("file1.txt", "a", append=True)
    assert data0 == Notefile("file1.txt").read().data
    o, _ = call("repair-metadata --dry-run", capture=True)
    assert data0 == Notefile("file1.txt").read().data
    assert o == "repaired (DRY-RUN): file1.txt\n"

    call("repair-metadata")  # to reset from above

    ## No hash
    writefile("file2.txt", "a")
    call("mod -t tag file2.txt --no-hash")
    note = Notefile("file2.txt").read()
    data0 = note.data.copy()
    assert not data0.get("sha256", None)

    data0 = note.data.copy()
    writefile("file2.txt", "a", append=True)
    assert data0 == Notefile("file2.txt").read().data
    o, _ = call("repair-metadata  --no-hash", capture=True)  # do not specify
    data = Notefile("file2.txt").read().data
    assert data0 != data
    assert o == "repaired: file2.txt\n"
    assert not data.get("sha256", None)

    data0 = Notefile("file2.txt").read().data
    writefile("file2.txt", "a", append=True)
    assert data0 == Notefile("file2.txt").read().data
    o, _ = call("repair-metadata", capture=True)  # do not specify
    data = Notefile("file2.txt").read().data
    assert data0 != data
    assert o == "repaired: file2.txt\n"
    assert data.get("sha256", None)

    ## Force
    writefile("file3.txt", "a")
    call("mod -t tag file3.txt --no-hash")
    assert not Notefile("file3.txt").read().data.get("sha256", None)

    o, _ = call("repair-metadata --dry-run --force-refresh", capture=True)
    assert o == (
        "repaired (DRY-RUN): file1.txt\n"
        "repaired (DRY-RUN): file2.txt\n"
        "repaired (DRY-RUN): file3.txt\n"
    )

    o, _ = call("repair-metadata --no-hash --force-refresh", capture=True)
    assert o == ("repaired: file1.txt\n" "repaired: file2.txt\n" "repaired: file3.txt\n")
    assert not Notefile("file3.txt").read().data.get("sha256", None)

    o, _ = call("repair-metadata --force-refresh", capture=True)
    assert o == ("repaired: file1.txt\n" "repaired: file2.txt\n" "repaired: file3.txt\n")
    assert Notefile("file3.txt").read().data.get("sha256", None)

    os.chdir(TESTDIR)


def test_orphan_repair():
    """
    Test unicode, etc
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "orphan-repair"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    # Repair with -V or -H unmatched?

    writefile("file1.txt", "this is the first file")
    call("mod -t tag file1.txt -H")

    Path("sub").mkdir(parents=True, exist_ok=True)

    # Make all kinds of copies....
    shutil.copy2("file1.txt", "file ONE.txt")
    shutil.copy2("file1.txt", "filewon.txt")
    shutil.copy2("file1.txt", "sub/file1.txt")  # Same leaf name
    writefile("filenot1.txt", "this is tHe first file")  # same mtime, size, wrong hash
    writefile("filenot1again.txt", "this is tHe first file.")  # Same mtime and nothing else

    stat = os.stat("file1.txt")
    os.utime("filenot1.txt", (stat.st_atime, stat.st_mtime))
    os.utime("filenot1again.txt", (stat.st_atime, stat.st_mtime))

    os.unlink("file1.txt")

    def warning_parse(txt):
        lines = txt.split("\n")[1:]
        lines = (line.strip() for line in lines)
        lines = (line for line in lines if line)
        lines = (line[2:] if line.startswith("./") else line for line in lines)
        return set(lines)

    call("find --orphaned --debug")

    # Default. too many
    _, e = call("repair", capture=True)
    assert warning_parse(e) == {"sub/file1.txt", "filewon.txt", "file ONE.txt"}

    # Max depth\
    _, e = call("repair --search-max-depth 0", capture=True)
    assert warning_parse(e) == {"filewon.txt", "file ONE.txt"}

    # Excludes
    _, e = call("repair --search-exclude '*one*'", capture=True)
    assert warning_parse(e) == {"filewon.txt", "sub/file1.txt"}

    _, e = call(
        "repair --search-exclude '*one*' --search-match-exclude-case --debug",
        capture=True,
    )
    assert warning_parse(e) == {"sub/file1.txt", "file ONE.txt", "filewon.txt"}

    # Search path (this is just one so dry-run it
    assert (
        call("repair --dry-run --search-path sub", capture=True)[0]
        == "(DRY RUN) .file1.txt.notes.yaml --> sub/.file1.txt.notes.yaml\n"
    )

    writefile("otherfile.txt", "another test")
    call("mod -t test --no-hash otherfile.txt")
    shutil.move("otherfile.txt", "other file.txt")
    o, e = call("repair-orphaned otherfile.txt.notes.yaml", capture=True)
    assert e == "WARNING: Cannot repair otherfile.txt based on hash since it's missing\n"

    # Test from a different location

    writefile("diff_dir.txt", "testing a different dir")
    call("mod -t test -V diff_dir.txt")
    shutil.move("diff_dir.txt", "sub/diff-dir.txt")
    try:
        os.chdir(os.path.expanduser("~"))
        call(f"repair-orphaned --path {dirpath}")
    finally:
        os.chdir(dirpath)
    assert os.path.exists("sub/diff-dir.txt.notes.yaml")

    os.chdir(TESTDIR)


def test_cat():
    """
    cat
    """
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "cat"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1")
    call('mod file1.txt -t tag -n "note"')

    o, _ = call("cat file1.txt", capture=True)
    assert o == "note\n"

    o, _ = call("cat file1.txt -f", capture=True)
    data = notefile.nfyaml.load_yaml(o)
    assert data["notes"] == "note"
    assert data["tags"] == ["tag"]

    os.chdir(TESTDIR)


def test_notefield():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "notefield"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1")

    call('mod file1.txt -t tag -n "this note" --note-field new')
    note = Notefile("file1.txt").read()
    assert note.data.new == "this note"
    assert note.data.notes == ""

    note = Notefile("file1.txt", note_field="new").read()
    assert note.data.new == "this note"
    assert "notes" not in note.data

    Path("tmp").unlink(missing_ok=True)

    call("grep this -o tmp")
    assert not Path("tmp").exists()

    call("grep this -o tmp --note-field new")  # same code as other searches
    assert readout("tmp") == {"file1.txt"}

    os.chdir(TESTDIR)


def test_nonstr():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "nonstr"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1")
    note = Notefile("file1.txt").read()
    note.data.notes = {"this": ["is", "a"], "dict": {"note": None}}
    note.write()

    # Searching should be done via a text representation
    call("grep agasdgasgd -o tmp")
    assert not Path("tmp").exists()

    call("grep dict -o tmp ")
    assert readout("tmp") == {"file1.txt"}

    try:
        call("mod -n 'new data' file1.txt --debug")
        assert False
    except TypeError:
        pass
    call("mod -n 'new data' file1.txt -R")  # Should work to replace!

    # note test_replace() already covers replace with non-text fields

    os.chdir(TESTDIR)


def test_auto_read():
    """test the new automatic read"""
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "autoread"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file1.txt", "file1")
    note = Notefile("file1.txt")

    # get data without having to call .read()
    assert note._data is None  # Not yet read
    note.data  # Should cause it to read
    assert note._data
    assert note._data is note.data

    # Call some methods that used to have errors
    Notefile("file1.txt").add_note("test")
    Notefile("file1.txt").cat()
    Notefile("file1.txt").isempty()
    Notefile("file1.txt").repair_metadata()

    # Check the debug
    with CaptureDebug() as de:
        note = Notefile("file1.txt")
        note.data
        note.data = "new"

    stderr = "".join(de.stderr)
    assert "DEBUG: Automatic read()" in stderr
    assert "DEBUG: data setter" in stderr

    os.chdir(TESTDIR)


def test_subdir():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "subdirs"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("subdir_vis.txt", "subdir_vis")
    writefile("subdir_hid.txt", "subdir_hid")
    writefile("no-subdir_vis.txt", "no-subdir_vis")
    writefile("no-subdir_hid.txt", "no-subdir_hid")

    call("mod subdir_vis.txt    -t tag --visible --subdir")
    call("mod subdir_hid.txt    -t tag --hidden  --subdir")
    call("mod no-subdir_vis.txt -t tag --visible --no-subdir")
    call("mod no-subdir_hid.txt -t tag --hidden  --no-subdir")

    assert {str(p) for p in Path(".").rglob("*.yaml")} == {
        "_notefiles/subdir_vis.txt.notes.yaml",
        ".notefiles/subdir_hid.txt.notes.yaml",
        "no-subdir_vis.txt.notes.yaml",
        ".no-subdir_hid.txt.notes.yaml",
    }

    # Make sure it doesn't change when I add a tag. Note the flags are all reverse
    call("mod subdir_vis.txt    -t tag2 --hidden  --no-subdir")
    call("mod subdir_hid.txt    -t tag2 --visible --no-subdir")
    call("mod no-subdir_vis.txt -t tag2 --hidden  --subdir")
    call("mod no-subdir_hid.txt -t tag2 --visible --subdir")

    assert {str(p) for p in Path(".").rglob("*.yaml")} == {  # same as above
        "_notefiles/subdir_vis.txt.notes.yaml",
        ".notefiles/subdir_hid.txt.notes.yaml",
        "no-subdir_vis.txt.notes.yaml",
        ".no-subdir_hid.txt.notes.yaml",
    }

    # Now change them
    call("vis hide subdir_vis.txt    --no-subdir")
    call("vis show subdir_hid.txt    --no-subdir")
    call("vis hide no-subdir_vis.txt --subdir")
    call("vis show no-subdir_hid.txt --subdir")

    assert {str(p) for p in Path(".").rglob("*.yaml")} == {
        ".notefiles/no-subdir_vis.txt.notes.yaml",
        "_notefiles/no-subdir_hid.txt.notes.yaml",
        ".subdir_vis.txt.notes.yaml",
        "subdir_hid.txt.notes.yaml",
    }

    # reset
    call("vis show subdir_vis.txt    --subdir")
    call("vis hide subdir_hid.txt    --subdir")
    call("vis show no-subdir_vis.txt --no-subdir")
    call("vis hide no-subdir_hid.txt --no-subdir")

    # Change vis without subdir flags
    call("vis hide subdir_vis.txt")
    call("vis show subdir_hid.txt")
    call("vis hide no-subdir_vis.txt")
    call("vis show no-subdir_hid.txt")

    assert {str(p) for p in Path(".").rglob("*.yaml")} == {
        ".notefiles/subdir_vis.txt.notes.yaml",
        "_notefiles/subdir_hid.txt.notes.yaml",
        ".no-subdir_vis.txt.notes.yaml",
        "no-subdir_hid.txt.notes.yaml",
    }

    findff = call("find -o res.txt")
    assert set(Path("res.txt").read_text().split()) == {
        "subdir_hid.txt",
        "no-subdir_hid.txt",
        "subdir_vis.txt",
        "no-subdir_vis.txt",
    }

    # Test again with a subdirectory
    writefile("asubdir/vis.txt", "in a subdir vis")
    writefile("asubdir/hid.txt", "in a subdir hid")
    call("mod asubdir/vis.txt -t tag --visible --subdir")
    call("mod asubdir/hid.txt -t tag --hidden --subdir")
    assert os.path.exists("asubdir/_notefiles/vis.txt.notes.yaml")
    assert os.path.exists("asubdir/.notefiles/hid.txt.notes.yaml")

    findff = call("find -o res.txt")
    assert set(Path("res.txt").read_text().split()) == {
        "subdir_hid.txt",
        "no-subdir_hid.txt",
        "subdir_vis.txt",
        "no-subdir_vis.txt",
        "asubdir/vis.txt",
        "asubdir/hid.txt",
    }


def test_pickle():
    os.chdir(TESTDIR)
    dirpath = TESTDIR / "pickle"
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    writefile("file.txt", "file")
    call("mod file.txt -t tag -n'some note'")
    note = Notefile("file.txt").read()

    new = pickle.loads(pickle.dumps(note))
    assert new.data == note.data
    assert new is not note


if __name__ == "__main__":
    #     test_mod()
    #     test_create_opts()
    #     test_copy()
    #     test_replace()
    #     test_change_viz_and_format(True)
    #     test_change_viz_and_format(False)
    #     test_change_tag()
    #     test_find_exclusions()
    #     test_outputs_export()
    #     test_search()
    #     test_links()
    #     test_unicode_spaces()
    #     test_notepath()
    #     test_metadata_repair()
    test_orphan_repair()
    #     test_cat()
    #     test_notefield()
    #     test_nonstr()
    #     test_auto_read()
    #     test_subdir()
    #     test_pickle()

    print("-=" * 50)
    print("SUCCESS")
