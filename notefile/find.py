"""
Main module-level utilities
"""

import os
import sys

from . import NOTESEXT
from .notefile import Notefile


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
    """Yield notes or raw paths discovered under one or more roots.

    Parameters
    ----------
    path:
        Starting path or collection of paths. Directories are searched
        recursively and honor exclusions. Explicit files are yielded directly
        and are not recursively expanded.
    excludes:
        Glob patterns to skip. Directory matches are checked with a trailing `/`.
    matchcase:
        Match exclude patterns case-sensitively.
    maxdepth:
        Maximum recursion depth where the starting directory is depth `0`.
    one_file_system:
        Prevent recursion across filesystem boundaries.
    exclude_links:
        Skip symlinked notes or symlinked filesystem entries.
    include_orphaned:
        Include orphaned notes whose targets no longer exist.
    empty:
        Filter by empty-note status. `None` disables this filter.
    noteopts:
        Keyword arguments passed to `Notefile` for yielded notes.

    Other Parameters
    ----------------
    filemode:
        Internal flag that yields raw file paths instead of `Notefile` objects.
    targetmode:
        Internal target-type filter used by CLI repair flows.

    Yields
    ------
    Notefile | str
        Matching notes, or raw paths when `filemode=True`. The `empty` filter
        distinguishes empty versus non-empty notes when note objects are being
        yielded.
    """
    filemode = kwargs.pop("filemode", False)  # Hidden argument
    targetmode = kwargs.pop("targetmode", "file")
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
                targetmode=targetmode,
            ):
                name = r if filemode else r.names0.filename
                if name not in seen:
                    yield r
                seen.add(name)
        return

    from .utils import _dot_sort, exclude_in_place

    if noteopts is None:
        noteopts = {}

    path = str(path)  # Path objects

    if os.path.isfile(path):
        yield Notefile(path, **noteopts) if not filemode else path
        return

    dev0 = os.stat(path).st_dev
    for root, dirs, files in os.walk(path):
        if filemode and targetmode in {"dir", "both"}:
            if not exclude_links or not os.path.islink(root):
                yield root

        # Do regular excludes of files
        exclude_in_place(
            files,
            excludes,
            matchcase=matchcase,
            isdir=False,
            remove_noteext=True,
            keep_notes_only=not filemode,
        )

        # Add subdirs but also check for excludes. Add them to files
        for subname in ["_notefiles", ".notefiles"]:
            try:
                dirs.remove(subname)  # will error if not here
                subfiles = os.listdir(os.path.join(root, subname))
                exclude_in_place(
                    subfiles,
                    excludes,
                    matchcase=matchcase,
                    isdir=False,
                    remove_noteext=True,
                    keep_notes_only=not filemode,
                )
                files.extend(os.path.join(subname, subfile) for subfile in subfiles)
            except ValueError:
                continue

        exclude_in_place(dirs, excludes, matchcase=matchcase, isdir=True)

        if one_file_system:
            dirs[:] = [d for d in dirs if os.stat(os.path.join(root, d)).st_dev == dev0]

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
                if targetmode == "dir":
                    continue
                if isnote or (exclude_links and os.path.islink(ffile)):
                    continue
                yield ffile
                continue

            if not isnote:
                continue

            nf = Notefile(ffile, **noteopts)
            if exclude_links and nf.islink:
                continue
            if targetmode != "both":
                if targetmode == "dir" and not nf.isdir0:
                    continue
                if targetmode == "file" and not nf.isfile0:
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
