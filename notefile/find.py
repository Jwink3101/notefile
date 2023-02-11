"""
Main module-level utilities
"""
from .notefile import Notefile
from . import NOTESEXT

import os, sys


def find(
    path=".",
    excludes=None,
    matchcase=False,
    maxdepth=None,
    one_file_system=False,
    exclude_links=False,
    include_orphaned=False,
    empty=None,
    noteopts=None,
    **kwargs,
):
    """
    find notes recurisvly starting in `path`

    Options:
    --------
    path ['.']
        Where to look. Can be a list/tuple too and will uniquely join them.
        Directories will recurse and follow exclusions. Files will ALWAYS return

    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended

    matchcase [False]
        Whether or not to match the case of the exclude file

    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    one_file_system [False]
        If True, do not cross filesystem boundaries.

    exclude_links [ False ]
        If True, will *not* return symlinked notes

    include_orphaned [ False ]
        If True, will ALSO return orphaned notes.
        Otherwise, they are excluded

    empty [None]
        None: Return all (also optimized)
        True: Only return empty notes
        False: Only return non-empty notes

    noteopts [{}]
        Options for the notefile created and returned

    Yields:
    -------
    note
        Notefile object

    """
    filemode = kwargs.pop("filemode", False)
    if kwargs:
        raise ValueError(f"Unrecognized arguments: {list(kwargs)}")

    if not path:
        path = ["."]

    if isinstance(path, (list, tuple, set)):
        seen = set()
        for p in path:
            for r in find(
                path=p,
                excludes=excludes,
                matchcase=matchcase,
                maxdepth=maxdepth,
                one_file_system=one_file_system,
                exclude_links=exclude_links,
                include_orphaned=include_orphaned,
                empty=empty,
                noteopts=noteopts,
                filemode=filemode,
            ):
                name = r if filemode else r.filename0
                if name not in seen:
                    yield r
                seen.add(name)
        return

    from .utils import exclude_in_place, _dot_sort

    if noteopts is None:
        noteopts = {}

    path = str(path)  # Path objects

    if os.path.isfile(path):
        yield Notefile(path, **noteopts) if not filemode else path
        return

    dev0 = os.stat(path).st_dev
    for root, dirs, files in os.walk(path):
        exclude_in_place(
            files,
            excludes,
            matchcase=matchcase,
            isdir=False,
            remove_noteext=True,
            keep_notes_only=not filemode,
        )
        exclude_in_place(dirs, excludes, matchcase=matchcase, isdir=True)

        if one_file_system:
            dirs[:] = [d for d in dirs if os.stat(os.path.join(root, d)).stdev == dev0]

        rel = os.path.relpath(root, path)
        depth = rel.count("/") + 1 if rel != "." else 0
        if maxdepth is not None and depth > maxdepth:
            del dirs[:]  # Do not go deeper
            continue

        files.sort(key=_dot_sort)
        dirs.sort(key=lambda s: s.lower())
        for file in files:
            ffile = os.path.join(root, file)
            isnote = file.lower().endswith(NOTESEXT)
            if filemode:
                if isnote or (exclude_links and os.path.islink(ffile)):
                    continue
                yield ffile
                continue

            if not isnote:
                continue

            nf = Notefile(ffile, **noteopts)
            if exclude_links and nf.islink:
                continue

            if nf.orphaned and not include_orphaned:
                continue

            if empty is not None:  # True or False
                isempty = nf.isempty()
                if empty and not isempty:
                    continue
                if not empty and isempty:
                    continue

            yield nf
