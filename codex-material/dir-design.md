# Directory Notes Design

## Purpose

This document captures the current design direction for supporting notefiles on directories without requiring a broad rewrite of the existing file-oriented model.

The goal is to support directory notes in a way that:

- preserves the current sidecar note model
- stays aligned with the existing CLI and API behavior
- supports repair for orphaned directory notes
- keeps tracking lightweight and understandable

This is now a directional design document rather than a list of competing proposals.

## Core Direction

Directories should be supported as first-class note targets.

The implementation should reuse the current storage model and most of the current behavior:

- notes still live in sidecar files
- hidden and subdir modes still apply
- directory notes should work with normal note editing, tagging, searching, and export
- orphaned directory notes should be supported, just as orphaned file notes are

The design is intentionally lightweight. Directory notes are mainly for human organization, not for deep content tracking.

## Note Placement

The note should live outside the directory, not inside it.

This is the most consistent choice with the existing file-sidecar model and avoids special rules for directory note storage.

Example target:

- `proj/`

Proposed note locations:

- visible note: `proj.notes.yaml`
- hidden note: `.proj.notes.yaml`
- visible subdir note: `_notefiles/proj.notes.yaml`
- hidden subdir note: `.notefiles/proj.notes.yaml`

This matches the existing filename resolution model closely and should minimize backend churn.

More explicitly, for a directory target:

- target: `somepath/subdir/`

the note lives in the parent directory `somepath/`, not inside `subdir/`.

So the note paths would be:

- visible note: `somepath/subdir.notes.yaml`
- hidden note: `somepath/.subdir.notes.yaml`
- visible subdir note: `somepath/_notefiles/subdir.notes.yaml`
- hidden subdir note: `somepath/.notefiles/subdir.notes.yaml`

## Target Identification

If the given path exists and is a directory, it is a directory target.

That applies to:

- CLI usage
- module usage

If the path does not exist, it should still be allowed, just as nonexistent file targets are effectively allowed today. In that case the target is simply orphaned until the directory exists again or is repaired.

There is no need for new `--dir` or `--file` creation flags for normal note creation.

## Data Model

Add a persisted `target-type` field.

This should be written for both kinds of targets:

- `target-type: file`
- `target-type: dir`

This simplifies orphan handling and removes ambiguity once the original target path no longer exists.

It also makes the behavior more explicit in exported data and future-proof for additional target-specific behavior.

## Directory Tracking Model

Directory tracking should be shallow and lightweight.

The tracked metadata should be based on first-level contents only, not recursive contents and not file contents.

### Tracked values

For directory notes, the tracked metadata should include:

- count of immediate subdirectories
- count of immediate non-note files
- a shallow normalized-name hash of immediate children

The normalized-name hash should be documented clearly in the docs as something equivalent to:

- `sha256(sorted(normalized_child_names))`

This is intentionally shallow:

- do not recurse into subdirectories
- do not hash file contents
- do not try to store a manifest
- use exactly the immediate children returned from `os.listdir()`

The point is to have lightweight directory identity and lightweight repair support, not deep verification.

It should be clear in the docs and the CLI that the coupling of directory to note is less strong than a hash.

### Normalization choice

For the shallow name hash, normalize child names by:

- using the immediate child names returned by `os.listdir()`
- sorting them lexically
- joining them in sorted order before hashing

Do not add more complicated normalization rules unless implementation pressure proves they are needed.

### Why shallow tracking

This matches the intended use better:

- low metadata churn
- cheap to compute
- useful enough for repair heuristics
- easier to explain than a recursive or content-based digest

It also avoids the complexity of deciding how note storage should affect recursive content hashes.

## Repair Model

Directory notes should support both:

- `repair-metadata`
- `repair-orphaned`

This is a required part of the design, not a later optional enhancement.

### Directory `repair-metadata`

This should recompute the tracked directory metadata:

- immediate subdirectory count
- immediate file count
- shallow name hash

This is the directory analogue of file metadata refresh.

### Directory `repair-orphaned`

This should search candidate directories and attempt to find the best match for an orphaned directory note.

The intended quick-search analogue to file `filesize` is:

- number of immediate subdirectories
- number of immediate non-note files

Additional matching signals:

- basename
- shallow name hash

The likely matching strategy should be:

1. narrow candidates with the cheap counts first
2. optionally use basename as another cheap filter
3. use the shallow name hash as the stronger discriminator

This keeps orphan repair practical without turning it into recursive directory indexing.

## Hidden Targets And Existing Gaps

Hidden directory targets should generally behave like hidden file targets.

This area already has edge cases even for files, so the directory implementation should:

- try to match existing behavior
- avoid overengineering hidden-directory edge handling in the first pass

The objective is consistency with the current model, not a total cleanup of every historical corner case.

## Symlinked Directories

Directory symlink behavior should be deferred.

The current symlink handling for files is already subtle, and extending full parity to directories would add substantial complexity for limited immediate value.

For the initial design:

- do not aim for full symlink-directory parity
- treat this as explicitly deferred work

## Special Paths

Special directory targets should be constrained.

Reject:

- `.`
- `..`

These are technically resolvable but awkward enough semantically that they are not worth supporting initially.

Trailing slash normalization should be supported:

- `proj`
- `proj/`

must resolve the same way.

## CLI Behavior

Most existing commands should continue to work once the backend understands directory targets.

### Commands expected to work with little conceptual change

- `mod`
- `edit`
- `cat`
- `copy`
- `replace`
- `format`
- `vis`
- `note-path`

### Search and query commands

Search-oriented commands should support a target-type filter:

- `--type {dir,file,both}`

This should apply to commands in the find/query/search family rather than to note creation.

The idea is:

- target type should be inferred from the path when creating or accessing a specific note
- target type should be selectable when searching across many notes

A `isdir` and `isfile` boolean should be defined for queries as well. The query docs should also include these new booleans.

### Display conventions

CLI output should distinguish directory notes by printing a trailing slash on the basename/path.

Example:

- file note output: `path/to/file.txt`
- directory note output: `path/to/proj/`

This should make the output more legible without adding extra metadata columns or persisted type fields.

For structured export, `target-type` should be included because it is part of the persisted note data.

## Backend Impact

The backend changes are still the main body of work, but they remain localized enough that this is not a rewrite.

Expected changes:

- generalize target existence checks so directories are valid targets
- teach `Notefile` initialization and read paths how to recognize directory targets
- add directory metadata collection
- add directory metadata repair
- add directory orphan repair
- extend finder/search filtering to distinguish file targets from directory targets
- adjust display and export behavior where target type affects output formatting

Areas likely to remain mostly unchanged:

- note serialization
- YAML/JSON handling
- tag handling
- note text editing
- grep/query logic over note content
- replace/copy semantics

## Testing Impact

The implementation will need a meaningful test expansion.

At minimum, tests should cover:

- creating notes on existing directories
- creating notes on nonexistent directory paths and treating them as orphaned
- hidden and visible directory notes
- subdir mode for directory notes
- `note-path` for directories
- `find` and related commands returning directory notes
- `--type {dir,file,both}` filtering
- `cat`, `mod`, `edit`, and tag operations on directory notes
- trailing slash normalization
- rejection of `.` and `..`
- directory metadata repair
- directory orphan repair
- output showing directory targets with a trailing slash
- queries with the booleans `isdir` and `isfile` for both files and directories.

The tests for directory repair should verify the shallow tracking rules explicitly so the behavior is stable and documented.

## Incremental Delivery Plan

### Phase 1: Core directory support

Implement:

- directory targets in `Notefile`
- sidecar path resolution using the existing model
- basic note read/write/edit/tag behavior
- `note-path`, `cat`, `mod`, `edit`, `copy`, `replace`, `format`, `vis`
- trailing-slash display for directory notes

### Phase 2: Search and filtering

Implement:

- `--type {dir,file,both}` for search-oriented commands
- finder support for distinguishing note target type cleanly

### Phase 3: Directory repair

Implement:

- shallow directory metadata collection
- `repair-metadata` for directory notes
- `repair-orphaned` for directory notes using shallow counts and shallow name hash

Symlink-directory behavior remains deferred beyond these phases.

## Effort Estimate

This still looks feasible without a broad refactor.

Rough estimate:

- core directory support: moderate
- search filtering and display cleanup: low to moderate
- shallow repair support for directories: moderate
- full symlink-directory parity: deferred because it would push complexity much higher

So the feature is real work, but it is not rewrite-level work.

## Worth The Effort

Given the clarified scope, this looks worth doing.

Reasons:

- attaching notes to directories is useful for project and folder organization
- the shallow tracking model keeps complexity bounded
- reuse of the current sidecar model reduces conceptual and implementation cost
- required repair behavior is still achievable without recursive content tracking

This would become much less attractive if it expanded into:

- recursive content hashing
- manifest storage
- full directory symlink parity

That is not the current plan.

## Final Direction Summary

The current design direction is:

1. Support directory notes as first-class targets.
2. Keep the note outside the directory using the existing sidecar placement model.
3. Persist `target-type` for both file and directory notes.
4. Allow nonexistent directory targets and treat them as orphaned, consistent with current file behavior.
5. Track directory metadata shallowly using first-level counts plus a shallow normalized-name hash.
6. Support directory `repair-metadata` and `repair-orphaned`.
7. Add `--type {dir,file,both}` to search-oriented commands.
8. Show directory targets in CLI output with a trailing slash.
9. Reject `.` and `..` as directory note targets.
10. Defer symlinked-directory semantics.

## Remaining Implementation Notes

These are not open product questions, but they should be handled carefully when coding:

- first-level children means exactly the entries returned by `os.listdir()` for the target directory
- hidden children are included if `os.listdir()` returns them
- the directory's own sidecar note is outside the directory, so it is not part of directory tracking
- subdir note-storage directories should only affect tracking if they are immediate children of the target directory
- make sure finder output formatting adds the trailing slash only for directory targets, not for note files themselves
- keep the directory behavior as close as practical to current file behavior where hidden/subdir modes are involved
