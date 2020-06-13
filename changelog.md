# Changelog

(**_newest_** on *top)

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
