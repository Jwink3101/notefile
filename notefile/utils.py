import os, sys

from . import debug, DT, warn


def now_string(Z=False):
    """
    Return an RFC3339 Time string
    
    Options:
    --------
    UTC [False]
        Give the time with UTC
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)  # this needs py 3.3+
    if Z:
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    now = now.astimezone()  # local time
    tz = now.strftime("%z")
    tz = f"{tz[:3]}:{tz[3:]}"  # Turn '-0700' to '-07:00'
    return now.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")


class Bunch(dict):
    """
    Based on sklearn's and the PyPI version, simple dict with 
    dot notation
    """

    def __init__(self, **kwargs):
        super(Bunch, self).__init__(kwargs)

    def __setattr__(self, key, value):
        self[key] = value

    def __dir__(self):
        return self.keys()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __repr__(self):
        s = super(Bunch, self).__repr__()
        return "Bunch(**{})".format(s)


def sha256(filepath, blocksize=2 ** 20):
    """
    Return the sha256 hash of a file. 
    
    `blocksize` adjusts how much of the file is read into memory at a time.
    This is useful for large files.
        2**20: 1 mb
        2**12: 4 kb
    """
    import hashlib

    hasher = hashlib.sha256()
    with open(filepath, "rb") as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()


def tmpfileinpath(dirpath):
    if not os.path.isdir(dirpath):
        dirpath = os.path.dirname(dirpath)
    return os.path.join(dirpath, ".notefile." + randstr(15))


def randstr(N=10):
    import math, string  # lazy

    letters = string.ascii_letters + string.digits
    Nl = len(letters)
    n = math.ceil(
        math.log(Nl) / math.log(256)
    )  # This could have been hardcoded but I like this more
    return "".join(letters[int.from_bytes(os.urandom(n), "little") % Nl] for _ in range(N))


def exclude_in_place(
    mylist, excludes, isdir=False, matchcase=False, remove_noteext=True, keep_notes_only=None
):
    """
    Helper tool to apply exclusions IN PLACE in mylist
    
    Options:
    --------
    isdir [False]
        Whether to also test for directories explicitly (trailing / on dirs)
    
    matchcase:
        Match case on exclusions
    
    remove_noteext [False]
        test and compare without NOTESEXT. Also assumes the main file
        does not have a . if the note is hidden
    
    keep_notes_only [None] {None,True,False}
        None: No Filters
        True: Removes *NON* notes
        False: Removes Notes
    
    """
    import fnmatch  # Lazy
    from . import NOTESEXT

    if excludes is None:
        excludes = []
    if isinstance(excludes, str):
        excludes = [excludes]

    if matchcase:
        case = lambda s: s
    else:
        case = lambda s: s.lower()
        excludes = [e.lower() for e in excludes]

    for item in mylist[:]:  # Iterate a copy!
        if (keep_notes_only is False and item.endswith(NOTESEXT)) or (
            keep_notes_only is True and not item.endswith(NOTESEXT)
        ):
            mylist.remove(item)
            continue

        item0 = item
        if item.endswith(NOTESEXT) and remove_noteext:
            item = item[: -len(NOTESEXT)]
            if item.startswith("."):
                item = item[1:]

        if any(fnmatch.fnmatch(case(item), e) for e in excludes):
            mylist.remove(item0)
            continue
        if isdir and any(fnmatch.fnmatch(case(item + "/"), e) for e in excludes):
            mylist.remove(item0)
            continue


def _dot_sort(file):
    file = file.lower()
    if file.startswith("."):
        return file[1:]
    return file


def symlink_file(src, dstdir):
    """
    Create a relative symlink from src to the dstdir. Note that the dest is
    a directory
    """
    dst = dst0 = os.path.join(dstdir, os.path.basename(src))

    for i in range(1, 100):  # Really shouldn't need 100. Make this an upper limit for safety
        if not os.path.exists(dst):
            break
        a, b = os.path.splitext(dst0)
        dst = a + ".{}".format(i) + b
        warn(f"{dst0} exists. Changing to {dst}")
    else:
        raise ValueError("Too many existing files with the same name")

    src = os.path.relpath(src, dstdir)

    try:
        os.makedirs(dstdir)
    except OSError:
        pass

    os.symlink(src, dst)
    debug(f"symlink {src} --> {dst}")
    return src


def flattenlist(*args):
    """Flatten out a list of lists matching strings (or non-iterable)"""
    for arg in args:
        if isinstance(arg, str):
            yield arg
        else:
            try:
                yield from flattenlist(*arg)
            except TypeError:  # Not iterable
                yield arg


# def fname_quote(name):
#     """Like shlex.quote but ALWAYS starts it with quotes and verifies it didn't break"""
#     import shlex
#     quoted = quoted0 = shlex.quote(name)
#     if quoted.startswith('"') or quoted.startswith("'"):
#         return quoted
#
