# Changelog

(**_newest_** on *top*)

## 2.20260109.0

- Changed the default --search-path for orphan repair to be the specified --path

## 2.20251207.0

- Defer hashing on new files until save

## On 2025-07-26 -- Just scripts

- Combined the behavior of macOS_Finder_tag into MacOStag_sync and changed the default

## 2.202400403.0

- Fixed bug with location of subdirs when specifying paths

## 2.20240310.1

- Made it pickleable to better enable parallel processing. Added test

## 2.20240310.0

- **New Feature**: Subdirs. Notes can now be placed in `_notefiles` or `.notefiles` instead of directly in the same directory
- Removed `v1` command and code. Not needed anymore.
- Better tag normalization

## 2.20230215.1

- Bug fix for `one_file_system`

## 2.20230215.0

- Allows you to enter tags with commas at the CLI. 
    - Example: `notefile mod -t "tag1,tag2" FILE`

## 2.20230212.0

- Added additional export formats. json and jsonl (line-delineated json).

## 2.20230211.0

- Cleanup documentation and code. Some Python Black commands must have gotten messed up because it was UGLY. Cleaned it up
- Saving a note makes it `.exist`

## 2.20230101.0

- Made the `Notefile` object call `.read()` automatically when needed. Added tests around this and cleaned up code that used to call `.read()`
- Updated documentation including in CLI

## 2.20221231.0

- For interactive edit, adds `--tags-only` flag and all `--full` edits are in YAML regardless of format

## 2.20221228.0

- Added `show` and `hide` as their own shortcut commands.
- Added `--orphaned` flag to `find`
- Repo Cleanup

## 2.20220409.0

- Combines `edit` and `mod` to one command with `edit` being a shortcut for `mod --edit`. This does *not change any interface*!

## 2.20220407.0

* Fixes a bug with queries grep and multiple expressions.
* Adds `gall` and `gany` to query.

## 2.20220404.0

* Fixes bug with `pathlib.Path` objects in `notefile.find`
* Minor fixed and improvements. Especially around the presentation of names

## 2.20220325.0

**New Version**

Way better backend that is much more usable. Many breaking changes on both the CLI and the Python API. Most notable on the Python side is `find_notes` is just `find`. The CLI is much easier to support and the help documents are better since they are broken up by need (e.g. exclusions are separate from queries). Another major change is that similar behavior is unified. For example, `grep` is just `find` with conditions. They all follow the same code paths (with minor optimizations) making testing and coding much easier. 

The older one is still included. Just call with `v1`. For example:

    $ notefile v1 search-tags ... 

(since `search-tags` is now just `tags`) or

```python
import notefile.v1 as notefile
# or
from notefile.v1 import Notefile
```

Some highlights:

- Updated CLI and Python API
- JSON mode. Can write the notes in JSON format which is faster to parse. Note that the extension doesn't change since YAML is a superset of JSON but the code tries to parse as JSON first.
- Better help 

------
# Version 1

## 20211216.0

* Adds information to edit
* Can edit more than one file at a time
* Fixes a bug in query with multiple grep expressions
* (known bug): Cannot `edit --full` an empty note. Will fix later

## 20210928.0

* Fixes as issue with flags in the `$EDITOR` environment variables

## 20210911.0

* Adds --count-order to search-tags

## 20210531.0

* Allow multi-line queries for the args. Note that they still do not do indentation, etc. Also accepts `-` as expression and will read from stdin to enable "heredocument" specification (so you don't have to escape quotes as much)

## 20210206.0:

* Minor fix for error formatting (left a debug). Minor cleanup

## 20210506.0

* Made `change-tag` allow you to change one tag to many

## 20210130.0:

* Changed `ruamel.yaml` to `ruamel_yaml`

## 20210114.0:

* Allows `export` of specific paths and no longer accepts `--path` for it
    * `export` can also accept stdin if given `-`. This now compliments `--export` on some flags but, for now, I'll keep both
* All paths are now `normpath`ed so change "`./item`" to "`item`". Tests updated
* Fixed python2 but I am not going to do anything else to preserve it!!!

## 20210106.0:

* Adds `--export` to grep and query. More to come
* Apparently breaks python2. May try to fix otherwise will update documentation

## 20210104.0:

* Adds `mod` (which also encompasses `tag`) to add notes to multiple files at the same time.
    * `add` is now deprecated but not sure when will be removed
* Refactor CLI. Still a mess but now easier to add new commands
* Moves some of the logic for `grep` and `query` into the Notefile object. This incurs a trivial performance cost but (a) adds those to Python object interaction and (b) makes more sense from design.
* **note**: A larger refactor of the CLI is underway

## 20201119.0:

* Allow `cat` on non-string notes. Still does not allow edit

## 20201105.0:

* Adds `--all-tags` to `search-tags` result which shows all tags that match

## 20201022.0:

* Changed `search-tags -t` to `-c` where `-c` is `--count`. Show counts rather than just a list

## 20201003.0:

* Fixed a minor bug with `cat -f` and the proper formatting

## 20201002.1:

* If pyyaml is installed, will use that to read notefiles (~2x) and if it is linked to LibYAML, ~25x.

## 20201002.0:

* Adds the function `tany()` (and `t()`) and `tall()` to query as a shortcut

## 20200930.0:

* Fixes a bug with `vis --dry-run` and no longer silently accepts error on them.

## 20200926.0:

* Adds `--empty` and `--non-empty` to `find`. An empty note means it has *NO* field besides metadata. It is *not* just notes, etc.

## 20200924.0

* Adds `--allow-exception` to query.

## 20200923.0 (and .1)

* Adds the ability to specify the field in which notes are written. Will grep and query a string representation but will not let you add text to it.
    * Does not (yet?) let you set the tags field
* `.1` fixes a minor bug in copy

## 20200915.0

* Adds `query` command to perform python queries. This works like `search-tags --filter` but lets you also query the notes and other fields.
    * Removes `--filter` from `search-tags` as the query replaces it
    * Note that `query` can replace all of `search-tags` and `grep` but adds a lot of boilerplate that those two remove. Also, `query` is slower than `grep` since `grep` avoids parsing YAML on all notes
* Tests updated to test `query` and remote `search-tags --filter`

## 20200905.0

* Adds `change-tag` command to rename specific tags.

## 20200724.0

* Fixes a bug where `.*` type exclude would exclude hidden notes on visible files. Also added a warning when using notefile on hidden files. Not recommended and untested

## 20200716.1

* Adds symlink result option to `find`, `grep` and `search-tags`. Removes the scripts that used to do this
* Adds note about know issues (will be fixed in the future)

## 20200716.0

* Bug fix for mtime repair

## 20200714.0

* Tag CLI has changed so that tags can be added or removed in one call. For example, in the past, to remove `old` and add `new`, you would do:
    ```
    $ notefile -t old -r file.ext
    $ notefile -t new file.ext
    ```
    and now it is
    ```
    $ notefile -t new -r old file.ext
    ```
    
* Does not modify a note if nothing has changed. This includes not making a new note if not changed

## 20200713.0

* Adds `--filter` to `search-tags` where the expression is interpreted as a Python ternary expression. Enables searches like `--filter "'tag1' in tags and not 'tag2' in tags"`
* Adds `--full-word` to match full words matches other. (adds `\b` to each side of the expression)

## 20200709.0

* Speed improvements to `grep`.  This change will drastically speed up grep when there aren't a ton of matches (as one would expect). I have some more improvements planned but this change goes a long way!

## 20200708.0

* Adds tag editing to interactive `edit` command

## 20200703.0

* Adds `-f/--full` flag to `edit` command to edit the YAML file

## 20200619.0

* Improved sorting to results to sort *regardless* of hidden (previously, hidden were found first)

## 20200613.0

* Adds `-0,--print0` to `grep` and `find` for better handling of spaces in filenames when piping to `xargs -0`. Adds tests for this as well.
    * Note that `search-tags` is always YAML output so this isn't needed
* `--debug` now prints to stderr

## 20200523.0

* Made metadata repair fix broken links if broken from changing the visibility f the  the referent (and added tests)
    * Moving the referent is not fixed!
* Bug fix for naming of broken linked notes
* Removed short flag for `--dry-run`

## 20200522.0
    
* Adds a `find` command. Basically just like `grep ""` but faster since it doesn't have to read the files
    
## 20200521.1

* Orphan repairs no longer take `-H` or `-V` and instead respect the hidden state of the original file

## 20200521.0

* Filename is no longer tracked metadata. It will not be removed from existing notes though. It was unneeded since the note itself had the filename and makes it *less* clear with links. See `scripts/remove_filename.py` to remove filenames
* Cleared up that orphaned repairs do NOT check mtime unless `--mtime` and added appropriate test.
* Bug Fixes:
    * Fixed a bug where dry run metadata repair would still rewrite the notefile even without (correctly) updating the file
    * Fixed a bug where a repair could overwrite an existing file
    
## 20200517.0

* Adds `-F` for grep (i.e. `re.escape` the query)
* Fixes shebang (I left `python2` for testing but python2 support will go away soon)

## 20200516.0

* Major rewrite under the hood to be more object oriented and better design. Also better non-CLI usage
* Add the ability to hide notes and, as such, adds the `--hidden` and `--visible` flags as well as `vis` functionality
* Adds a `copy` mode (and associated tests)
* Compatibility Issues:
    * Removed fancy tag queries. Now just `or` unless `--all`. Use the module functions (`find_notes`,`Notefile(filename).read().data['tags']`)
    * Any non-CLI usage is probably broken now. Sorry. But it *should* be easier to fix!
    * By the new design, if the note is created with `--no-hash`, it won't get a hash unless repaired with `--force-refresh` or the underlying file has been modified (This behavior is now tested)
* Other minor bug fixes and improvements
        
## 20200506.0 

* Add `--all` mode to `grep` (and internally handle multiple expressions differently).
* Remove header in interactive edit
* Minor cleanup and additions to debug mode. Still WIP
