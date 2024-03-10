## Paths

Notefiles can have four types of paths depending on `--hidden`/`--visible` and `--subdir`/`--no-subdir` (`--no-subdir` is implied but present for completeness)

For `file.ext`

| flags | `--hidden` | `--visible` |
|--|--|--|
| **`--subdir`** | `.notefiles/file.ext.notes.yaml` | `_notefiles/file.ext.notes.yaml` |
| **`--no-subdir`** | `.file.ext.notes.yaml` | `file.ext.notes.yaml` |



## To Do

Incomplete list

- X find
- CLI
    - Create
    - show/hide
- move / copy / replace
- repair
- show/hide
    - Half done. Need to add check to make sure multiple do not exist.
-  test excludes with hidden modes