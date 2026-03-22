# Tag Values Thought Experiment

## Goal

Describe a backward-compatible design for optional tag values in `notefile`, plus an implementation plan detailed enough that the feature could be built later without needing the original discussion context.

This document is intentionally more detailed than a changelog note and less rigid than a formal spec.

## Summary

The proposed design adds optional values to tags while preserving the current meaning of plain tags.

Key decisions:

- Internally, tags are normalized to a mapping of `{tag_name: value_or_none}`.
- On disk, the existing `tags` field is kept, but its serialized representation becomes a mixed collection:
  - a bare string means the tag exists and has no value
  - a one-entry mapping means the tag exists and has a value
- Existing query semantics for plain tags remain unchanged.
- Existing CLI operations for plain tags remain unchanged.
- New query and CLI behavior is additive and explicit.

Example YAML:

```yaml
tags:
  - tag1
  - status: open
  - flag: true
  - owner: "Alice"
```

Example JSON:

```json
{
  "tags": [
    "tag1",
    {"status": "open"},
    {"flag": true},
    {"owner": "Alice"}
  ]
}
```

## Why This Design

The point of valued tags is not just storage convenience. The main benefit is reducing tag taxonomy drift and replacing ad hoc prefix conventions such as:

- `status-open`
- `status-closed`
- `priority-high`
- `priority-low`
- `owner-alice`

Valued tags let one conceptual tag key carry a small parameter:

- `status=open`
- `priority=high`
- `owner=alice`

This becomes worthwhile when:

- the tag has one obvious key and a variable value
- values are small scalars rather than freeform note text
- users want to query both by presence of the key and by the specific value
- current usage has multiple mutually exclusive prefixed tags for one concept

It is less worthwhile when:

- plain presence/absence tags are already sufficient
- values would be long text
- values would become multi-valued or nested
- the main motivation is aesthetics rather than queryability or taxonomy control

## Important Constraint: Backward Compatibility

This feature must not break old notes or old user habits.

That means:

- old notefiles containing `tags: ["tag1", "tag2"]` must continue to work unchanged
- existing CLI uses like `mod -t tag1` and `search --tag tag1` must continue to work
- existing query helpers such as `t('tag1')`, `tany(...)`, and `tall(...)` must continue to operate on tag names only
- old code paths that conceptually care only about tag presence should not be forced to care about tag values

This also means that changing the on-disk format is acceptable only if:

- old files are still valid input
- the new format is unambiguous
- normalized writing remains deterministic

## Proposed Data Model

### Internal Canonical Representation

After reading, tags should be normalized into a mapping:

```python
{
    "tag1": None,
    "status": "open",
    "flag": True,
}
```

Properties of the internal model:

- tag names are normalized exactly as current tags are normalized:
  - lowercase
  - stripped
- a tag with no value stores `None`
- a valued tag stores a scalar value
- duplicate tag declarations are resolved with "last wins"
- internal callers should use this normalized representation rather than the raw serialized `data["tags"]` list

Rationale:

- this is the cleanest in-memory model
- it preserves the one-tag-one-value invariant
- it simplifies queries and future extension
- it avoids forcing all internal logic to work on raw mixed collections

### External Serialized Representation

On disk, `tags` remains the field name, but becomes a list whose elements may be either:

- a string: tag exists with no value
- a one-entry mapping: tag exists with a value

Examples:

- `"tag1"` means `tag1 -> None`
- `{"status": "open"}` means `status -> "open"`
- `{"flag": true}` means `flag -> True`

Properties:

- duplicate tags are allowed on read, but not preserved semantically
- if duplicates occur, later entries override earlier ones
- write output should be canonical and deterministic, not source-preserving
- write order should remain sorted by tag name, consistent with current normalization behavior

Rationale:

- preserves the existing `tags` field name
- allows old notes to remain valid
- works naturally in both YAML and JSON
- makes value-bearing tags human-readable in YAML

## Rejected Alternative: Separate `tag-values` Field

A separate structure such as:

```yaml
tags: [status, priority]
tag-values:
  status: open
  priority: high
```

would be safer operationally, but was rejected for this thought experiment.

Why it was not chosen:

- it splits one conceptual feature across two fields
- it introduces synchronization rules between `tags` and `tag-values`
- the mixed serialization is more compact and arguably more intuitive for human readers
- the internal dict model already handles the semantics cleanly

Why it remained attractive:

- lower implementation risk
- lower chance of hidden assumptions breaking
- easier compatibility for code that still thinks tags are strings

If implementation risk later proves too high, reverting to the separate-field design is the safest fallback.

## Read Semantics

### Accepted Input Forms

The reader should accept all of the following:

```yaml
tags: []
```

```yaml
tags:
  - tag1
  - tag2
```

```yaml
tags:
  - tag1
  - status: open
  - flag: true
```

### Normalization Rules

When reading `data["tags"]`:

1. If no `tags` field exists, treat it as empty.
2. If an item is a string:
   - normalize the string as a tag name
   - store `tag_name -> None`
3. If an item is a mapping:
   - it must contain exactly one key
   - normalize the key as the tag name
   - store `tag_name -> raw_value`
4. If a tag appears multiple times, the last occurrence wins.
5. Empty normalized tag names are invalid and should raise an error.
6. Any non-string, non-one-entry-mapping tag item is invalid and should raise an error.

### Boolean Compatibility

There is already a compatibility fix for YAML 1.1 / 1.2 handling of plain tags like `yes` and `no`.

That logic must be reconsidered once valued tags exist:

- bare tag names must still be treated as names, not accidentally coerced values
- valued entries such as `{"flag": true}` should preserve the actual boolean value

Important distinction:

- bare `yes` as a tag name should remain a tag name
- `flag: true` should remain a boolean

## Write Semantics

When writing:

1. Normalize all internal tag state into the canonical dict representation.
2. Sort by normalized tag name.
3. Serialize each tag as:
   - bare string if value is `None`
   - one-entry mapping if value is not `None`

This means write output is normalized semantic output, not a byte-for-byte round trip.

That matches current behavior, where tags are already normalized and re-sorted on write.

## CLI Input Design

### Motivation

The current CLI tag parser splits on commas very aggressively. That is sufficient for plain tag names but not robust enough for values that may themselves contain commas.

Valued tags should therefore move to a proper CSV-like parsing layer for tag input.

### Proposed Tag Input Syntax

Examples:

- `tag1`
- `status=open`
- `flag=true`
- `owner="Alice Smith"`
- `"tag with spaces"="value, with comma"`

Rules:

1. Parse the overall input as CSV fields.
2. For each field:
   - strip surrounding whitespace after CSV decoding
   - split on the first `=`
3. Left side:
   - required
   - tag name
   - strip whitespace
   - lowercase
4. Right side:
   - if absent, value is `None`
   - if present but empty after stripping, value is `None`
   - otherwise preserve as a value

### Tag Name Rules

- tag names remain normalized the same way as current tags
- `=` is not allowed in tag names
- commas are only allowed via CSV quoting

### Value Rules for v1

Values need a deliberately limited v1 policy.

Recommended v1:

- strings are allowed
- booleans are allowed via case-insensitive `true` and `false`
- numbers are not auto-coerced and remain strings
- empty right-hand side means `None`

Examples:

- `status=open` -> `"open"`
- `flag=true` -> `True`
- `flag=False` -> `False`
- `ticket=123` -> `"123"`
- `tag=` -> `None`

Rationale:

- boolean coercion is useful and easy to explain
- number coercion is more ambiguous and easy to regret
- keeping numbers as strings avoids accidental type surprises in v1

### Explicit Non-Goals for v1

Do not add in v1:

- automatic numeric coercion
- nested values
- lists as tag values
- YAML-style implicit scalar parsing

Avoid YAML-style coercion because it is surprising at the CLI and introduces edge cases like `yes`, `on`, `off`, and `null`.

## Query Design

### Compatibility Requirement

Existing queries must keep working.

That means `tags` in the query namespace should remain the set or frozenset of tag names only, not the internal dict.

These existing query forms should continue to work:

- `t('status')`
- `tany('a', 'b')`
- `tall('a', 'b')`
- `any(t.startswith('status') for t in tags)`
- `any('bla' in t for t in tags)`

### Additive Query Surface

Add new query namespace bindings:

- `tag_values` or `tagvals`: a dict of tag name to value, including `None`
- `tv(name)`: return the value for a tag or `None`
- `tval(name, expected)`: return `True` iff the tag exists and equals the expected value

Examples:

```python
t('status') and tv('status') == 'open'
```

```python
tv('flag') is True
```

```python
any(name.startswith('status') for name in tags)
```

### Why Not Replace `tags` in Queries

Do not make `tags` become a dict in the query namespace.

Reasons:

- it breaks existing membership semantics
- it breaks existing comprehensions over names
- it forces every current query user to relearn the API

Keep the current name-oriented query API stable and add a value-aware API alongside it.

## CLI Search and Modification Design

### Existing Behavior to Preserve

These must continue to operate on tag names only:

- `mod -t tag1`
- `mod -r tag1`
- `search --tag tag1`
- `tags`
- `change-tag old new` when used on name-only tags

### New Additive CLI Operations

Recommended additions:

- `mod --tag-value status=open`
- `mod --tag-value flag=true`
- `mod --remove-tag-value status`

Semantics:

- `--tag-value status=open` sets or replaces the value for `status`
- `--tag-value status=` means `status -> None`
- `--remove-tag-value status` removes only the value and keeps the tag as a plain tag
- `--remove status` removes the entire tag, including any value

This is safer than overloading all existing `-t/--tag` behavior immediately.

Possible future extension:

- allow `-t status=open` as shorthand once the parser is mature

That shorthand should not be the first implementation target unless the parser refactor is already done and well tested.

### Search Flags

Recommended additive flags:

- `search --tag-value status=open`
- `search --tag-value-exists status`
- `search --tag-value-missing status`

These are optional if the `query` command is considered sufficient, but dedicated flags may be justified if valued tags become common.

### `tags` Command

The existing `tags` command should remain name-oriented by default.

Reasons:

- preserves old behavior
- keeps output simple
- avoids changing the meaning of tag counts and tag-mode aggregation

Possible additive behaviors:

- `tags --show-values`
- a separate `tag-values` command

This should be deferred unless there is a clear use case.

## Output and Display Design

### `cat -t`

Current behavior should remain name-oriented unless an explicit flag is added.

Possible future option:

- `cat -t --with-values`

Without that flag:

- show just the normalized tag names

With that flag:

- show normalized key/value representation

### Tag-Mode Output

Current `--tag-mode` output groups results by tag name.

This should remain unchanged in v1.

Do not change `--tag-mode` to group by `key=value` pairs by default.

Reasons:

- the current command is conceptually "which tags are present in the result set"
- grouping by valued pairs is a different feature
- changing it would surprise users

Possible future extension:

- `--tag-mode=pairs`
- `--tag-pairs`

## `change-tag` Design Considerations

This command becomes more subtle once tags can have values.

Questions:

- should renaming `status` to `state` preserve the value?
- should `change-tag status state` transform `status=open` into `state=open`?

Recommended answer:

- yes, renaming the tag name should preserve the associated value

Examples:

- `status` -> `state`
- `status=open` -> `state=open`

If multiple tags collapse due to rename, the later normalized rule should win or the command should raise. This requires an explicit decision during implementation. The safer choice is probably "destination wins deterministically after normalization" with documentation.

## Copy / Replace / Append Behavior

Current `replace --field tags` and append logic assume tags are string-like collections.

With valued tags:

- `--field tags` should continue to mean the full tag structure, including values
- append should merge by tag name
- if the same tag exists in both source and destination:
  - an explicit collision rule is needed

Recommended append rule:

- destination tag values are overridden by source tag values during append

Rationale:

- append already conceptually means "bring source content into destination"
- this matches the "last wins" normalization model

This should be documented and tested carefully.

## Interactive Edit Considerations

Interactive tag editing currently assumes plain comma-separated tags.

Once valued tags exist, there are two choices:

1. keep the current simple editor for name-only tags and do not support valued tags there initially
2. upgrade the tag editing line to the new CSV-style syntax

Recommended path:

- eventually upgrade interactive tag editing to the CSV-style syntax
- but do not make it the first implementation step

Reason:

- interactive parsing increases regression risk
- the core feature can ship without immediately updating the manual edit path

If deferred, the UI/help text must state that interactive tags-only edit is name-only until upgraded.

## Error Handling

Invalid `tags` entries in files should fail loudly rather than guessing.

Examples of invalid raw forms:

- `tags: [123]`
- `tags: [{a: 1, b: 2}]`
- `tags: [null]`
- empty normalized tag names

Invalid CLI input should produce actionable error messages:

- "Empty tag name"
- "Invalid valued tag syntax"
- "Only one '=' split is supported; '=' is not allowed in tag names"

## Migration Risk

The main risk is not serialization itself. The risk is hidden assumptions throughout the code that `data["tags"]` is a list of strings.

Examples of high-risk areas:

- normalization helpers
- read/write paths
- copy/replace append logic
- comparison / `ismod()`
- `modify_tags()`
- query namespace setup
- tag-mode display
- interactive edit
- any tests that directly compare `data["tags"]` to string lists

To reduce risk:

- introduce a small internal tag API layer first
- convert internal callers to use it
- only then change serialization and CLI parsing

## Recommended Internal API Layer

Before changing feature behavior, add internal helper functions or methods such as:

- `normalize_tag_items(raw_tags) -> OrderedDict[str, object | None]`
- `serialize_tag_items(tag_map) -> list`
- `tag_names(tag_map) -> list[str]`
- `tag_name_set(tag_map) -> set[str]`
- `set_tag_value(tag_map, name, value)`
- `remove_tag(tag_map, name)`
- `remove_tag_value(tag_map, name)` sets value to `None`

If desired, add `Notefile` methods such as:

- `get_tag_map()`
- `set_tag_map(tag_map)`
- `modify_tag_values(...)`

This layer is the key to avoiding scattered, inconsistent logic.

## Implementation Todo Plan

### Phase 1: Prepare the Internals

1. Audit all code paths that directly assume `data["tags"]` is a string list.
2. Add internal normalization and serialization helpers for tag maps.
3. Add tests for helper behavior only:
   - plain tags
   - valued tags
   - duplicate tags with last-wins
   - invalid raw forms
   - canonical write ordering

Why first:

- this isolates the core semantics
- it reduces the chance of partial migration bugs

### Phase 2: Read / Write Support

1. Update `read()` logic to accept mixed `tags` items.
2. Normalize raw tags into the internal tag map.
3. Ensure the rest of the `Notefile` instance sees a stable tag abstraction.
4. Update `writes()` to serialize the canonical map back into mixed `tags`.
5. Preserve old note compatibility.

Tests:

- old YAML notes still read and rewrite correctly
- old JSON notes still read and rewrite correctly
- mixed YAML tags round-trip semantically
- mixed JSON tags round-trip semantically

### Phase 3: Internal Callers

1. Update `modify_tags()` to operate on the internal tag map.
2. Update copy/replace append logic to merge by tag name.
3. Update `ismod()` comparison to compare normalized tag maps rather than string sets.
4. Update any direct iteration over `note.data.tags` to use tag-name helpers where appropriate.

Tests:

- add/remove plain tags still works
- tag removal removes any associated value
- append and replace respect the collision rule
- no regressions in existing tag behavior

### Phase 4: Query Support

1. Keep `tags` in query as names-only.
2. Add `tag_values` / `tagvals`.
3. Add helper functions such as `tv()` and `tval()`.
4. Update query help text.
5. Add tests for:
   - `tv('status') == 'open'`
   - `tv('flag') is True`
   - existing string-tag queries still work
   - comprehensions like `any(t.startswith('status') for t in tags)` still work

Why before CLI:

- query is likely the most powerful and lowest-risk user-facing access path for the feature

### Phase 5: CLI Write Support

1. Introduce explicit valued-tag CLI options:
   - `--tag-value`
   - `--remove-tag-value`
2. Add a CSV-style parser for tag/value inputs.
3. Define and implement the v1 value coercion rules.
4. Update `mod` handling to use the tag API layer.
5. Add tests for:
   - plain tags still parse the same
   - valued tags parse correctly
   - commas in quoted values
   - empty values map to `None`
   - boolean coercion for `true`/`false`

### Phase 6: CLI Search Support

1. Decide whether dedicated search flags are needed immediately.
2. If yes, add:
   - `--tag-value`
   - `--tag-value-exists`
   - `--tag-value-missing`
3. Implement them in the search filter path.
4. Add tests for combined query/tag/value cases.

If this phase feels too broad, defer it and rely on `query` support first.

### Phase 7: Secondary Commands

1. Update `change-tag` to preserve values when renaming tag names.
2. Decide collision behavior during rename.
3. Review `cat -t`, `tags`, and `--tag-mode`.
4. Preserve old default outputs unless an explicit new flag is added.

Tests:

- `change-tag old new` preserves values
- tag aggregation remains name-oriented by default

### Phase 8: Interactive Edit

1. Decide whether interactive tag editing should support valued tags in the first release.
2. If yes, migrate the edit syntax to the CSV-style format.
3. If not, document the limitation clearly and keep behavior stable.

This should be one of the last steps because it has a high parsing and UX regression risk.

### Phase 9: Documentation

1. Update CLI help text.
2. Update `readme.md` examples if the feature is user-facing.
3. Add changelog notes.
4. Document:
   - mixed `tags` serialization
   - query helpers
   - CLI parser rules
   - duplicate tag "last wins" rule
   - boolean-only coercion for v1

## Recommended Minimal Delivery Slice

If implementing incrementally, the safest first shipping slice is:

1. internal tag map support
2. mixed read/write support
3. query support with `tv()` / `tag_values`
4. explicit `mod --tag-value`

Defer:

- `-t key=value` shorthand
- search flags beyond query
- interactive edit updates
- specialized display changes

This slice captures the core value of the feature while minimizing parser and UX churn.

## Open Questions for Future Revisit

- Should numeric values ever be coerced automatically?
- Should `tags` in Python-facing APIs remain list-like in some places for compatibility, or should a new accessor be mandatory?
- Should there be a separate output mode for key/value tag aggregation?
- How should rename collisions behave in `change-tag`?
- Should bare tag names that parse as booleans in YAML continue to receive compatibility conversion, and how should that interact with valued tags?

## Final Recommendation

If this feature is ever implemented, do it as a deliberate refactor with an internal tag abstraction first.

The mixed serialization format is defensible and compatible enough, but only if the code stops treating `data["tags"]` as "just a list of strings" internally.

The safest core principles are:

- internal canonical dict
- external mixed `tags` sequence
- last wins on duplicate declarations
- queries keep `tags` name-oriented
- value-aware behavior is additive and explicit
- CLI parser moves to a CSV-style dialect before supporting inline values broadly
