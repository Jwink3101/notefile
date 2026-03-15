import os
import sys

from . import DT, debug, warn


def now_string(Z=False):
    """Return the current time as an RFC 3339 timestamp.

    Parameters
    ----------
    Z:
        When true, emit the timestamp in UTC with a trailing `Z`. Otherwise,
        include the local timezone offset.
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
        """Initialize the mapping from keyword arguments."""
        super(Bunch, self).__init__(kwargs)

    def __setattr__(self, key, value):
        """Mirror attribute assignment into dictionary storage."""
        self[key] = value

    def __dir__(self):
        """Expose stored keys for tab completion and introspection."""
        return self.keys()

    def __getattr__(self, key):
        """Resolve unknown attributes from the dictionary contents."""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __repr__(self):
        """Return a constructor-like representation for debugging."""
        s = super(Bunch, self).__repr__()
        return "Bunch(**{})".format(s)


def sha256(filepath, blocksize=2**20):
    """Hash a file with SHA-256.

    Parameters
    ----------
    filepath:
        File to read.
    blocksize:
        Number of bytes to stream per read. Useful for large files.
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
    """Return a random temporary filename alongside `dirpath`."""
    if not os.path.isdir(dirpath):
        dirpath = os.path.dirname(dirpath)
    return os.path.join(dirpath, ".notefile." + randstr(15))


def randstr(N=10):
    """Return a cryptographically random alphanumeric string."""
    import math  # lazy
    import string

    letters = string.ascii_letters + string.digits
    Nl = len(letters)
    n = math.ceil(
        math.log(Nl) / math.log(256)
    )  # This could have been hardcoded but I like this more
    return "".join(letters[int.from_bytes(os.urandom(n), "little") % Nl] for _ in range(N))


def exclude_in_place(
    mylist,
    excludes,
    isdir=False,
    matchcase=False,
    remove_noteext=True,
    keep_notes_only=None,
):
    """Filter a list of names in place using glob-style exclusions.

    Parameters
    ----------
    mylist:
        Mutable list of filenames or directory names to edit.
    excludes:
        Glob patterns to remove from the list.
    isdir:
        When true, also test each item as a directory name with a trailing `/`.
    matchcase:
        Match exclude patterns case-sensitively.
    remove_noteext:
        Compare notefile names without the `.notes.yaml` suffix. Hidden note
        names are also compared without the leading dot.
    keep_notes_only:
        `True` keeps only note files, `False` removes note files, and `None`
        disables that extra filter.
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
    """Sort helper that ignores a leading dot."""
    file = file.lower()
    if file.startswith("."):
        return file[1:]
    return file


def symlink_file(src, dstdir):
    """Create a relative symlink to `src` inside `dstdir`.

    The destination is treated as a directory. If the destination name already
    exists, a numeric suffix is appended until a free path is found.
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
    """Yield a recursive flattening of nested iterables while preserving strings."""
    for arg in args:
        if isinstance(arg, str):
            yield arg
        else:
            try:
                yield from flattenlist(*arg)
            except TypeError:  # Not iterable
                yield arg


def normalize_tags(tags, sort=True):
    """Normalize tags into a deduplicated collection.

    Parameters
    ----------
    tags:
        String or iterable of strings. Comma-separated tags are split without
        escaping, converted to lowercase, and stripped of surrounding whitespace.
    sort:
        When true, return a sorted list. Otherwise return a set.
    """
    if isinstance(tags, str):
        tags = [tags]

    # Split tags with commas in them. Do not try to escape commas. It isn't
    # worth the pain!
    tags = flattenlist(*(tag.split(",") for tag in tags))

    # lower and stripped
    tags = {tag.strip().lower() for tag in tags}

    if not sort:
        return tags

    return sorted(tags)
