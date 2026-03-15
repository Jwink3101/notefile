# Directory Notes Implementation ToDo

## Purpose

This document is the working implementation checklist for directory-note support in `notefile`.

It should be kept current so work can resume later without reconstructing context from chat history or memory.

## Current Status

Status: `implemented`

Last updated: `2026-03-14`

Current focus:

- feature implemented and verified

Known blockers:

- none

Deferred intentionally:

- directory symlink parity
- recursive directory tracking
- manifest-style directory tracking
- broader README / generated help refresh beyond the implemented query-help changes

## Agreed Semantics

- directory targets are first-class note targets
- the note lives outside the directory, in the parent directory
- hidden and subdir note-placement modes still apply
- `target-type` is persisted for both file and directory notes
- nonexistent directory targets are allowed and treated as orphaned
- directory tracking is shallow only
- shallow tracking uses immediate children only, meaning exactly `os.listdir()`
- no recursive directory tracking
- no file-content hashing for directory tracking
- directory notes support `repair-metadata`
- directory notes support `repair-orphaned`
- search-oriented commands support `--type {dir,file,both}`
- query context exposes `isdir` and `isfile`
- human-readable CLI output shows directory targets with a trailing `/`
- `.` and `..` are rejected as direct targets

## Implemented Metadata

Persisted fields:

- `target-type`
- `filesize` and `sha256` for file targets
- `dir-subdirs`, `dir-files`, and `dir-hash` for directory targets

Directory rules:

- immediate children means exactly the entries returned by `os.listdir()`
- hidden children are included if `os.listdir()` returns them
- `dir-hash` is based on sorted immediate child names
- `dir-files` counts immediate non-note, non-directory children
- the ordinary sidecar note for a directory target is outside the directory, so it does not affect directory tracking
- `_notefiles` and `.notefiles` count if they are immediate children of the target directory

## Implemented Work

### Backend

Status: `completed`

- generalized `Notefile` target handling for files and directories
- added persisted `target-type`
- added shallow directory metadata collection
- added support for orphaned nonexistent directory targets
- extended `repair-metadata` for directories
- extended `repair-orphaned` for directories
- preserved existing file-note behavior

Primary files changed:

- [notefile/notefile.py](/Users/jwinokur/git_home/notefile/notefile/notefile.py)
- [notefile/find.py](/Users/jwinokur/git_home/notefile/notefile/find.py)

### CLI

Status: `completed`

- added `--type {dir,file,both}` to search-oriented commands
- added trailing `/` display for directory targets in human-readable output
- preserved canonical path values in structured export keys
- fixed an existing `repair-orphaned` CLI output prefix bug encountered during implementation

Primary file changed:

- [notefile/cli.py](/Users/jwinokur/git_home/notefile/notefile/cli.py)

### Query Support

Status: `completed`

- added `isdir` and `isfile` to safe and unsafe query namespaces
- updated query help text for the new booleans

Primary file changed:

- [notefile/__init__.py](/Users/jwinokur/git_home/notefile/notefile/__init__.py)

### Tests

Status: `completed`

- added directory note creation coverage
- added nonexistent directory target coverage
- added directory metadata and repair coverage
- added type filter coverage
- added query boolean coverage
- added trailing-slash output coverage
- adjusted test workspace handling to avoid repo-local symlink issues in this environment

Primary file changed:

- [tests.py](/Users/jwinokur/git_home/notefile/tests.py)

## Remaining Follow-Up Work

Status: `optional`

- update broader user docs in [readme.md](/Users/jwinokur/git_home/notefile/readme.md)
- regenerate or refresh generated CLI docs if desired
- decide whether to expose directory metadata fields more explicitly in user documentation
- decide whether null-delimited output should always include the display slash exactly as line output does
- revisit directory symlink semantics only if there is a concrete user need

## Verification Checklist

- [x] existing file-note tests still pass
- [x] directory note creation works
- [x] directory note placement matches the parent-directory rule
- [x] nonexistent directory targets are treated as orphaned
- [x] `target-type` is persisted correctly for files and directories
- [x] shallow directory metadata is written correctly
- [x] shallow tracking uses only immediate `os.listdir()` entries
- [x] directory `repair-metadata` works
- [x] directory `repair-orphaned` works
- [x] `--type {dir,file,both}` works
- [x] query booleans `isdir` and `isfile` work
- [x] CLI output shows directory targets with trailing `/`
- [ ] broader docs updated

## Verification Run

Last full verification command:

```bash
pytest tests.py -q
```

Last result:

- `27 passed, 7 warnings`

## Session Log

- `2026-03-14`: created implementation ToDo from the design document.
- `2026-03-14`: implemented directory-note support, added target typing, shallow directory repair/tracking, CLI type filters, query booleans, trailing-slash display, and tests; full suite passed.
