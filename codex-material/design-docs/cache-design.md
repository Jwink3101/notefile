# Cache Design Thought Experiment

## Goal

Describe a minimal-change design for an optional SQLite cache in `notefile` that:

- keeps the note file authoritative
- avoids many small file reads and repeated parsing
- avoids filesystem checks when cache use is enabled
- can later support cache-backed `find` and search without rewriting query semantics first

This document is meant to be detailed enough to guide implementation later without needing the original discussion context.

## Summary

The proposed design adds an optional, central SQLite cache that is:

- read-through on `Notefile.read()`
- write-through on `Notefile.write()`
- trusted by default when enabled
- off by default in v1
- keyed by absolute paths, with canonical-path rows plus alias lookups

The cache is secondary storage. The note file remains authoritative on write.

When cache is enabled:

- direct note operations should read from cache first
- cache misses fall back to disk and repopulate cache
- `find` and search-style commands should be able to enumerate cache-backed notes instead of walking the filesystem
- Python filtering semantics should be reused in v1 rather than reimplemented in SQL

The intent is to remove as much filesystem traffic as possible while changing as little code as possible.

## Why This Design

The motivating problem is not primarily `O(n)` search complexity. The bigger issue is latency from:

- walking directories
- repeated `stat()`-style probes
- opening many small note files
- reparsing YAML or JSON over and over

This design treats the cache as the default read source when enabled, rather than as a mere helper index.

That matters because a minimal "search candidates from cache, then verify from disk" approach would reintroduce the exact filesystem cost this feature is trying to avoid.

## Core Decisions

These decisions were converged during the design discussion:

- Cache remains optional in v1 and is off by default.
- `NOTEFILE_USE_CACHE` enables cache use.
- `NOTEFILE_CACHE_DB` overrides the default SQLite database location.
- A global CLI override should also exist: `--cache` and `--no-cache`.
- When cache is disabled for a run, both cache reads and cache writes are bypassed.
- When cache is enabled, normal reads trust the cache and do not validate against the filesystem.
- `Notefile.write()` still writes the note file first and updates cache second.
- Cache update failure after a successful file write is non-fatal.
- Cache misses should fall back to disk and repopulate the cache.
- `find` should be cache-backed in v1 when cache is enabled.
- `find` and search should reuse existing Python filtering logic in v1.
- Rebuild should be simple: clear the cache, then repopulate from filesystem truth.
- Maintenance surface should stay minimal: `cache build` and `cache clear`.

## Configuration

### Environment Variables

- `NOTEFILE_USE_CACHE`
  - enables cache usage when truthy
  - cache remains off by default when unset
- `NOTEFILE_CACHE_DB`
  - overrides the default SQLite cache location

### CLI Overrides

Global flags should be added:

- `--cache`
- `--no-cache`

Suggested precedence:

1. CLI flag
2. `NOTEFILE_USE_CACHE`
3. default off

### Default Database Location

If `NOTEFILE_CACHE_DB` is unset, use:

`~/.cache/notefile/notefile-cache.sqlite3`

This gives a conventional user-scoped central cache while keeping repository trees clean.

## Scope

### V1 Goals

- Add a central SQLite cache module.
- Make `Notefile.read()` cache-backed when enabled.
- Make `Notefile.write()` update cache after successful file writes.
- Allow `find` and search-style commands to enumerate cache entries instead of the filesystem.
- Keep query and tag semantics in Python rather than SQL.
- Add minimal maintenance commands.
- Keep the implementation as non-invasive as possible.

### Non-Goals for V1

- SQL-native implementation of grep, tag, or query semantics
- public stable cache serialization APIs
- pickled or serialized full Python `Notefile` objects
- mandatory validation against the filesystem during normal cache-backed reads
- aggressive denormalized search/index schema tuned for performance first

## High-Level Architecture

The smallest implementation surface is to add one new cache module and hook it into existing seams.

### New Module

Add a new internal module, for example:

- [`notefile/cache.py`](/Users/jwinokur/git_home/notefile/notefile/cache.py)

Responsibilities:

- open/configure SQLite
- initialize schema
- check schema version
- fetch cache records by absolute path
- store/update canonical rows and aliases
- iterate cached entries for cache-backed `find`
- clear and build helpers

This module should remain an adapter. It should not become a second copy of `Notefile` logic.

### Existing Integration Points

Only a few existing seams need to change:

1. [`notefile/notefile.py`](/Users/jwinokur/git_home/notefile/notefile/notefile.py)
   - `read()`
   - `write()`
   - internal cache-record helpers
2. [`notefile/find.py`](/Users/jwinokur/git_home/notefile/notefile/find.py)
   - branch between filesystem-backed and cache-backed enumeration
3. [`notefile/cli.py`](/Users/jwinokur/git_home/notefile/notefile/cli.py)
   - parse cache flags
   - wire maintenance commands

That keeps the change localized and reversible.

## Data Model

Do not pickle `Notefile` instances.

Instead, cache a stable, versioned record made from two parts:

- normalized note data
- minimal resolved state needed to reconstruct a `Notefile` without probing the filesystem

### Main Table

Conceptual table: `notes`

Suggested fields:

- `canonical_note_path` TEXT PRIMARY KEY
- `primary_target_path` TEXT NOT NULL
- `record_version` INTEGER NOT NULL
- `state_json` TEXT NOT NULL
- `data_json` TEXT NOT NULL
- `updated_at` TEXT or INTEGER

Notes:

- `canonical_note_path` is the canonical row identity.
- `data_json` stores the fully normalized note data as JSON.
- `state_json` stores the minimal reconstruction state.

### Alias Table

Conceptual table: `aliases`

Suggested fields:

- `alias_path` TEXT PRIMARY KEY
- `canonical_note_path` TEXT NOT NULL

Reason:

- requested paths, symlink/source lookups, and notefile variants should not force row duplication
- separate alias rows are simpler and more queryable than JSON arrays inside the main row

### Versioning

Use both:

- a DB schema version
- a per-record `record_version`

Reason:

- schema layout may evolve independently from payload shape
- resolved-state payloads are likely to change as edge cases are discovered

On incompatible records:

- fail closed
- fall back to disk
- repopulate cache

## Cache Record Shape

Two internal helpers should be added to `Notefile`:

- `_to_cache_record()`
- `from_cache_record()`

These should be internal for v1, not public API.

### `data_json`

`data_json` should contain the full normalized note data as JSON.

Reason:

- a cache hit should avoid YAML parsing entirely
- it should also avoid re-running ordinary normalization work
- this preserves existing Python query/tag logic with minimal changes

This should store the normalized data as `Notefile.read()` would expose it, not a raw note-file text blob.

### `state_json`

`state_json` should contain the minimum state needed to reconstruct a cache-backed `Notefile` instance.

Suggested fields:

- `filename`
- `filename0`
- `destnote`
- `destnote0`
- `exists`
- `exists0`
- `is_hidden`
- `is_hidden0`
- `is_subdir`
- `is_subdir0`
- `islink`
- `link`
- `target_type`
- `target_type0`
- `orphaned`
- `format`
- `format0`

The exact set can be refined during implementation, but the rule should be:

- include only what is required to rebuild a usable read-only `Notefile`
- do not store arbitrary internal object state just because it exists

## `Notefile` Construction Strategy

Do not use subclassing first.

Instead:

- keep the ordinary constructor for disk-backed initialization
- add a `classmethod` `from_cache_record()` for cache-backed reconstruction

Reason:

- normal constructor semantics remain intact
- cache-backed construction is explicit
- fewer mixed-mode bugs than adding constructor flags

### `from_cache_record()`

This method should:

- create a `Notefile` instance without normal filesystem-heavy initialization
- populate the required path and state attributes from `state_json`
- load `_data` from `data_json`
- initialize `_data0` consistently
- fail closed if required state is missing or incompatible

### `_to_cache_record()`

This method should:

- emit the canonical note path
- emit all absolute alias paths
- emit normalized `data_json`
- emit minimal `state_json`

## Read Path

When cache is enabled, [`Notefile.read()`](/Users/jwinokur/git_home/notefile/notefile/notefile.py#L348) should become read-through.

Suggested control flow:

1. Attempt cache lookup by absolute path.
2. If a matching alias exists, resolve to the canonical row.
3. If the record is present and compatible:
   - materialize from `from_cache_record()`
   - return without reading the note file
4. If the record is missing or incompatible:
   - run the existing disk-backed read logic
   - normalize as usual
   - store/update the cache
   - return

Important v1 policy:

- no normal validation against the filesystem on cache hit

This is essential to the design goal of avoiding filesystem traffic.

## Write Path

[`Notefile.write()`](/Users/jwinokur/git_home/notefile/notefile/notefile.py#L486) should remain authoritative and mostly unchanged.

Suggested control flow:

1. serialize and atomically write the real note file exactly as today
2. rebuild links exactly as today
3. attempt to update the cache from the current in-memory note state
4. treat cache failure as non-fatal

This preserves the core source-of-truth contract:

- the file is authoritative
- the cache is secondary

## Cache-Backed `find`

When cache is enabled, [`notefile/find.py`](/Users/jwinokur/git_home/notefile/notefile/find.py) should enumerate cache rows instead of walking the filesystem.

However, v1 should not move full `find` semantics into SQL.

### V1 Approach

- fetch candidate rows lazily from SQLite
- materialize cached `Notefile` instances lazily
- apply existing path, exclude, depth, and filtering semantics in Python

Reason:

- minimal semantic drift
- minimal code churn
- preserves current behavior more easily

This is intentionally not the most optimized SQL design. It is the lowest-risk design that still avoids `os.walk()` and many per-note filesystem checks.

## Search and Query Behavior

V1 should reuse the existing Python filtering model.

That means:

- tag filtering should continue to use current Python logic
- query evaluation should continue to use current Python logic
- grep/query/tag parity should come from reconstructing `Notefile` state from cache, not from reimplementing behavior in SQL

Reason:

- lower implementation risk
- lower parity risk
- smaller code changes

This is the main reason storing normalized `data_json` is important.

## Direct Single-Note Operations

When cache is enabled, direct commands such as:

- `cat file`
- `mod file`

should also use cache first unless explicitly disabled.

If a cached note is modified and then written:

- `write()` should recreate or overwrite the authoritative note file as needed
- cache should then be refreshed from the new in-memory state

This avoids a pre-write filesystem probe while preserving file authority at commit time.

## Cache Maintenance Commands

Keep maintenance minimal in v1.

Suggested CLI:

- `notefile cache clear`
- `notefile cache build`

### `cache clear`

- delete the whole cache database

This is intentionally simple in a single global DB.

### `cache build`

Behavior:

1. clear the cache database
2. repopulate from filesystem truth

Implementation principle:

- do not build a fancy special-purpose reconciliation engine
- use ordinary authoritative reads and ordinary cache population mechanisms as much as practical

This keeps the codepath easier to trust.

## Cache Usage Rules

### When Cache Is Disabled

- bypass cache reads
- bypass cache writes

This keeps `--no-cache` or disabled environment behavior easy to reason about.

### When Cache Is Enabled

- trust cache on reads
- do not validate against the filesystem during normal operations
- populate cache on read-through miss
- update cache after successful writes

### Repair Commands

Repair-style commands should prefer disk truth where they need it.

Reason:

- their purpose is to reconcile or repair filesystem reality
- using cache by default there would be counterproductive

## Tradeoffs

### Advantages

- minimal note-file format impact
- minimal search/query semantic rewrite
- real reduction in note-file reads and reparsing
- real reduction in filesystem traversal when cache-backed `find` is used
- centralized and configurable storage
- reversible rollout because cache is off by default

### Costs

- more internal state-management complexity in `Notefile`
- cache-backed reconstruction must be kept semantically aligned with disk-backed construction
- stale cache is accepted until explicit rebuild/clear or read-through repopulation
- v1 is not maximally SQL-optimized

## Why Not Pickle `Notefile`

Pickling or otherwise serializing the full Python object was considered and rejected.

Reasons:

- brittle across code changes
- poor robustness across versions
- unstable internal attribute surface
- harder to inspect and migrate than explicit JSON payloads

Explicit versioned records are more work than a pickle at first, but much safer over time.

## Why Not Subclass `Notefile` First

Subclassing was also considered and rejected as the starting point.

Reason:

- the difficult part is not inheritance
- the difficult part is faithfully reconstructing enough state to preserve behavior

A dedicated `from_cache_record()` constructor path is simpler and more explicit than teaching a subclass to partially bypass filesystem-backed initialization.

## Recommended Implementation Order

1. Add cache configuration plumbing.
2. Add `notefile/cache.py` with schema setup, get/put, alias lookups, and clear helpers.
3. Add internal `Notefile._to_cache_record()`.
4. Add internal `Notefile.from_cache_record()`.
5. Hook `Notefile.read()` into cache read-through.
6. Hook `Notefile.write()` into best-effort cache updates.
7. Add `cache clear`.
8. Add `cache build`.
9. Add cache-backed `find()` enumeration.
10. Reuse current Python search/tag/query filtering unchanged.

This order gives useful wins early while keeping each step small and testable.

## Testing Priorities

Any implementation should emphasize parity and fallback safety.

Suggested tests:

- cache disabled behaves exactly as today
- cache-enabled read hits avoid disk-backed parse path
- cache miss falls back to disk and repopulates cache
- write updates cache after successful file write
- cache incompatibility falls back to disk and repopulates
- `find` can enumerate from cache when enabled
- query/tag/grep semantics match current behavior on cache-backed notes
- symlink/source and hidden/subdir variants resolve correctly through alias lookups
- `cache clear` removes the DB
- `cache build` rebuilds from filesystem truth

## Final Recommendation

Build the cache in the smallest coherent way:

- cache-backed `Notefile.read()`
- cache-updating `Notefile.write()`
- cache-backed `find`
- Python-side filtering unchanged
- maintenance limited to `cache clear` and `cache build`

That gives the biggest practical reduction in filesystem traffic for the least invasive code change, while keeping the note file authoritative and leaving room for future SQL-side optimization if it ever becomes worthwhile.
