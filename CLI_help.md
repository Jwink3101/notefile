# CLI Help

Not all alias commands are listed (e.g., `grep` is an alias for `search --grep` and isn't included). `query` is still included for the additional help. `v1` is also excluded

# No Command


```text
usage: notefile [-h] [--debug] [--note-field field] [--version] command ...

MAIN

optional arguments:
  -h, --help          show this help message and exit

Global Options:
  --debug             Debug mode
  --note-field field  Specify the field in the notes to read/write. Defaults
                      to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version           show program's version number and exit

Commands:
  Run `notefile.py <command> -h` for help

  command
    mod               Modify notes. Edit interactivly, add or replace notes,
                      add or remove tags
    edit              Shortcut for 'notefile.py mod --edit'
    copy              Copy the notes from SRC to DST(s). DST must not have any
                      notes
    replace           Replace/Update some or all of the content in SRC to
                      notes in DST
    change-tag        Change one tag to another (or multiple) and display the
                      results
    vis               Change the visibility of file(s)/dir(s)
    show              Shortcut for 'notefile.py vis show'
    hide              Shortcut for 'notefile.py vis hide'
    format            Change the format of file(s)/dir(s)
    repair            Repair notefile(s): metadata and orphaned
    repair-metadata   Repair notefile(s): metadata
    repair-orphaned   Repair notefile(s): orphaned
    cat               Print the note
    find              Find and list all notes
    export            Shortcut for 'notefile.py find --export'. Note, can use
                      'notefile.py search --export <search flags>' if needed
                      with search queries.
    search            Find and list all notes with criteria
    grep              Shortcut for 'notefile.py search --grep'
    query             Shortcut for 'notefile.py search --query'. Also has
                      additional details on queries
    tags              Shortcut for 'notefile.py search --tag-mode --tag'
    note-path         Return the path to the notefile (or potential file if
                      the note doesn't yet exist)
    v1                Call the older notefile tool with all args passed to it.
                      Example: 'notefile v1 search-tags'. v1 will *read* JSON
                      but cannot *write* it. Will be DEPREACTED soon.

```

# mod


```text
usage: notefile mod [-h] [-e] [-f] [-m] [--tags-only] [-r TAG] [-t TAG]
                       [-R] [-n NOTE] [-s] [--link {source,symlink,both}] [-H]
                       [-V] [--no-hash] [--no-refresh] [--format {json,yaml}]
                       [--rewrite-format] [--debug] [--note-field field]
                       [--version]
                       file [file ...]

positional arguments:
  file                  Specify file(s)

optional arguments:
  -h, --help            show this help message and exit

Interactive Edit:
  Edit notes with a text editor. Other modifications come first

  -e, --edit            Launch $EDITOR to interactivly edit the notes for a
                        file
  -f, --full            Edit the full YAML file. Will always edit in YAML mode
                        even if notes are stored in JSON
  -m, --manual          Instead of $EDITOR, print the path and then wait for
                        user-input to continue
  --tags-only           Just edit tags, not both

Modify Notes:
  Add or replace notes. Add or remove tags

  -r TAG, --remove TAG  Specify tags to remove
  -t TAG, --tag TAG, -a TAG, --add TAG
                        Specify tags to add
  -R, --replace         Replace rather than append the new note
  -n NOTE, --note NOTE  Notes to add (or replace). Each argument is its own
                        line. Specify `--note ""` to add empty line. Notes
                        will come _after_ stdin if applicable
  -s, --stdin           Read note from stdin. Prepended to any --note
                        arguments

Create/Modify Options:
  Flags for creating and saving notes. Not all flags are always applicable!

  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

```

# copy


```text
usage: notefile copy [-h] [--link {source,symlink,both}] [-H] [-V]
                        [--no-hash] [--no-refresh] [--format {json,yaml}]
                        [--rewrite-format] [--debug] [--note-field field]
                        [--version]
                        SRC DST [DST ...]

positional arguments:
  SRC                   Source note
  DST                   Destination file. Must not have ANY notes

optional arguments:
  -h, --help            show this help message and exit

Create/Modify Options:
  Flags for creating and saving notes. Not all flags are always applicable!

  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

```

# replace


```text
usage: notefile replace [-h] [--link {source,symlink,both}] [-H] [-V]
                           [--no-hash] [--no-refresh] [--format {json,yaml}]
                           [--rewrite-format] [--debug] [--note-field field]
                           [--version] [--field FIELD] [--all-fields]
                           [--append]
                           SRC DST [DST ...]

positional arguments:
  SRC                   Source note
  DST                   Destination file

optional arguments:
  -h, --help            show this help message and exit
  --field FIELD         Specify fields to replace/update. If NONE are
                        specified, will use --note-field. If ANY flag is set,
                        will only do them. For example, `--field tags` will
                        *only* replace/update tags. To do tags and notes, do
                        `--field tags --field notes`. Will NOT raise any alert
                        if field is not in the source
  --all-fields          Ignore --fields and do all fields. This is effectively
                        `copy` with allowing it to overwrite existing notes
  --append              Update/append rather than replace the contents in each
                        field. With the exception of `tags`, the field values
                        must either be text-based or the dest must not have
                        anything in the field

Create/Modify Options:
  Flags for creating and saving notes. Not all flags are always applicable!

  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

```

# change-tag


```text
usage: notefile change-tag [-h] [--debug] [--note-field field] [--version]
                              [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                              [--match-exclude-case] [--max-depth N] [-x] [-0]
                              [--export] [--tag-mode] [--tag-counts]
                              [--tag-count-order] [-o FILE] [--symlink DIR]
                              [--link {source,symlink,both}] [-H] [-V]
                              [--no-hash] [--no-refresh]
                              [--format {json,yaml}] [--rewrite-format] [-n]
                              old new [new ...]

positional arguments:
  old                   old tag to change
  new                   new tag(s)

optional arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         Do not make changes

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

Create/Modify Options:
  Flags for creating and saving notes. Not all flags are always applicable!

  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

```

# vis


```text
usage: notefile vis [-h] [--debug] [--note-field field] [--version]
                       [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                       [--match-exclude-case] [--max-depth N] [-x] [-0]
                       [--export] [--tag-mode] [--tag-counts]
                       [--tag-count-order] [-o FILE] [--symlink DIR] [-n]
                       {hide,show} [path ...]

positional arguments:
  {hide,show}           Visibility mode for file(s)/dir(s)
  path                  Additional --path arguments

optional arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         Do not make changes

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

```

# format


```text
usage: notefile format [-h] [--debug] [--note-field field] [--version]
                          [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                          [--match-exclude-case] [--max-depth N] [-x] [-0]
                          [--export] [--tag-mode] [--tag-counts]
                          [--tag-count-order] [-o FILE] [--symlink DIR] [-n]
                          {yaml,json} [path ...]

positional arguments:
  {yaml,json}           Change the note format for file(s)/dir(s)
  path                  Additional --path arguments

optional arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         Do not make changes

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

```

# repair


```text
usage: notefile repair [-h] [--debug] [--note-field field] [--version]
                          [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                          [--match-exclude-case] [--max-depth N] [-x]
                          [--link {source,symlink,both}] [-H] [-V] [--no-hash]
                          [--no-refresh] [--format {json,yaml}]
                          [--rewrite-format] [--dry-run] [--force-refresh]
                          [--match {size,mtime,hash,name}]
                          [--search-path SEARCH_PATH]
                          [--search-exclude SEARCH_EXCLUDE]
                          [--search-exclude-links]
                          [--search-match-exclude-case] [--search-max-depth N]
                          [--search-one-file-system]
                          [path ...]

positional arguments:
  path                  Additional --path arguments

optional arguments:
  -h, --help            show this help message and exit

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

Create/Modify Options:
  Flags for creating and saving notes. Not all flags are always applicable!

  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

Repair Options:
  --dry-run             Do not make any changes

Repair metadata options:
  --force-refresh       Force notefile.py repair to refresh all metadata
                        (while still respecting --no-hash)

Repair orphaned options:
  --match {size,mtime,hash,name}
                        Specify how to search for matches. Specify multiple as
                        needed. 'size' is ALWAYS implied but is the only
                        attribute if '--match size' is the sole flag. Default
                        is '--match mtime --match hash' (with '--match size'
                        implied). Specifying '--match name' means the the
                        moved file must have the same name (aka leaf). Note:
                        will ONLY match if there is only a single candidate so
                        more requirements is also more likely to match. Use
                        --dry-run if needed to test!
  --search-path SEARCH_PATH
                        Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --search-exclude SEARCH_EXCLUDE
                        Specify a glob pattern to exclude when looking for
                        files. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --search-exclude-links
                        Do not include symlinked files
  --search-match-exclude-case
                        Match case on exclude patterns
  --search-max-depth N  Specify the maximum depth to search for files. The
                        current directory is 0
  --search-one-file-system
                        Do not cross filesystem boundaries when searching for
                        a file

```

# cat


```text
usage: notefile cat [-h] [--debug] [--note-field field] [--version] [-f]
                       [-t]
                       file

positional arguments:
  file                Specify file to cat

optional arguments:
  -h, --help          show this help message and exit
  -f, --full          Display the full YAML note rather than just the note
                      text
  -t, --tags          Display the tags

Global Options:
  --debug             Debug mode
  --note-field field  Specify the field in the notes to read/write. Defaults
                      to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version           show program's version number and exit

```

# find


```text
usage: notefile find [-h] [--debug] [--note-field field] [--version]
                        [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                        [--match-exclude-case] [--max-depth N] [-x] [-0]
                        [--export] [--tag-mode] [--tag-counts]
                        [--tag-count-order] [-o FILE] [--symlink DIR]
                        [--orphaned]

optional arguments:
  -h, --help            show this help message and exit
  --orphaned            Find orphaned notes only. Does not repair. See repair-
                        orphaned to repair

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

```

# search


```text
usage: notefile search [-h] [--debug] [--note-field field] [--version]
                          [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                          [--match-exclude-case] [--max-depth N] [-x] [--all]
                          [--grep expr] [--fixed-strings] [--full-note]
                          [--full-word] [--match-expr-case] [--query expr]
                          [-e] [-t TAG] [--tag-all] [-0] [--export]
                          [--tag-mode] [--tag-counts] [--tag-count-order]
                          [-o FILE] [--symlink DIR]

optional arguments:
  -h, --help            show this help message and exit
  --all                 Match for all. Default is ANY

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

grep options:
  Search for string matches

  --grep expr           Search for text. Follows python regex patterns unless
                        --fixed-strings. May need to escape them for bash
                        parsing. Can specify multiple. If note contents are
                        not strings, will use the `str()` representation
  --fixed-strings       Match the string literally without regex patterns for
                        grep expression
  --full-note           grep the full note, not just the notes
  --full-word           Matches the full word(s) of the grep expression. (adds
                        \b)
  --match-expr-case     Match case on grep expression

query options:
  Advanced Python queries. See 'query -h' for details.

  --query expr          Query expression. Can be multiple lines delineated by
                        \n or ';' but the last line must evaluate to True or
                        False as the query. Set as `-` to read stdin
  -e, --allow-exception
                        Allow exceptions in the query. Still prints a warning
                        to stderr for each one

tag search options:
  -t TAG, --tag TAG     Specify tag to find
  --tag-all             Match all specified tags

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

```

# query


```text
usage: notefile query [-h] [--debug] [--note-field field] [--version]
                         [-p PATH] [--exclude EXCLUDE] [--exclude-links]
                         [--match-exclude-case] [--max-depth N] [-x] [--all]
                         [--grep expr] [--fixed-strings] [--full-note]
                         [--full-word] [--match-expr-case] [--query expr] [-e]
                         [-t TAG] [--tag-all] [-0] [--export] [--tag-mode]
                         [--tag-counts] [--tag-count-order] [-o FILE]
                         [--symlink DIR]
                         [query ...]

positional arguments:
  query                 Additional queries added to any --query.

optional arguments:
  -h, --help            show this help message and exit
  --all                 Match for all. Default is ANY

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

find Options:
  Flags for finding notes

  -p PATH, --path PATH  Specify path(s). Can specify multiple. Directories
                        will recurse and follow exclusions, etc. Specified
                        files will not. If not specified, will be '.'. If any
                        path is specified, will ONLY use those paths.
  --exclude EXCLUDE     Specify a glob pattern to exclude when looking for
                        notes. Directories are also matched with a trailing
                        '/'. Can specify multiple times.
  --exclude-links       Do not include symlinked notefiles
  --match-exclude-case  Match case on exclude patterns
  --max-depth N         Specify the maximum depth to search for notes. The
                        current directory is 0
  -x, --one-file-system
                        Do not cross filesystem boundaries

grep options:
  Search for string matches

  --grep expr           Search for text. Follows python regex patterns unless
                        --fixed-strings. May need to escape them for bash
                        parsing. Can specify multiple. If note contents are
                        not strings, will use the `str()` representation
  --fixed-strings       Match the string literally without regex patterns for
                        grep expression
  --full-note           grep the full note, not just the notes
  --full-word           Matches the full word(s) of the grep expression. (adds
                        \b)
  --match-expr-case     Match case on grep expression

query options:
  Advanced Python queries. See 'query -h' for details.

  --query expr          Query expression. Can be multiple lines delineated by
                        \n or ';' but the last line must evaluate to True or
                        False as the query. Set as `-` to read stdin
  -e, --allow-exception
                        Allow exceptions in the query. Still prints a warning
                        to stderr for each one

tag search options:
  -t TAG, --tag TAG     Specify tag to find
  --tag-all             Match all specified tags

Display Options:
  Some flags will be ignored and/or are mutually exclusive

  -0, --print0          Terminate names with a null byte. For use with `xargs
                        -0` when filenames have space
  --export              Export notes rather than printing names or tags
  --tag-mode            Displays results in terms of *all* tags present in the
                        results
  --tag-counts          Displays results with the counts of *all* tags present
                        in the results. Implies --tag-mode
  --tag-count-order     Orders the results by number of tags. Implies --tag-
                        mode
  -o FILE, --output FILE
                        Write results to FILE instead of stdout
  --symlink DIR         Create symlinks in DIR to the found files. If used in
                        --tag-mode, will also have subdirs with the name (or
                        filter). If there are name conflicts, will add `.N` to
                        the filename and print a warning to stderr

Queries:
--------
Queries are single expression statements that evaluate to True or False and
based on the note. It is evaluated as Python (with no sandboxing or sanitizing
so do not evaluate untrusted input). The following variables are defined:

    note    Notefile object including attributes such as 'filename',
            'destnote','hidden', etc. See Notefile documention
    data    Dictionary of the note
    notes   == data['notes']. The note text
    tags    == data['tags']. Set of tags (note, all lower case)
    text    Raw YAML of the note

And it includes the following functions:

    grep    performs a match against 'notes'. Respects the flags:
            '--match-expr-case','--fixed-strings','--full-word' automatically but 
            can also be overridden with the respective keyword arguments
    
    g       Aliased to grep
    
    gall    Essentially grep with match_any = False
    
    gany    Essentially grep with match_any = True
    
    tany    Returns True if that tag is in tags: e.g
                tany('tag1','tag2') <==> any(t in tags for t in ['tag1','tag2'])
    
    tall    Returns true if all args are in tags:
                tall('tag1','tag2') <==> all(t in tags for t in ['tag1','tag2'])
    
    t       aliased to tany
    
It also includes the `re` module and `ss = shlex.split`

Queries can replace search-tags and grep but grep is faster if it can be used since it 
is accelerated by not parsing YAML unless needed.

For example, the following return the same thing:

    $ notefile grep word1 word2 
    $ notefile query "grep('word1') or grep('word2')"    
    $ notefile query "grep('word1','word2')"
    $ notefile query "grep(ss('word1 word2'))" # can use shlex.split (ss) 

However, queries can be much more complex. For example:

    $ notefile query "(grep('word1') or grep('word2')) and not grep('word3')"

Limited multi-line support exists. Multiple lines can be delineated by ';'. 
However, the last line must evaluate the query. Example:

    $ notefile query "tt = ['a','b','c']; all(t in tags for t in tt)"
    
Can also pass STDIN with the expression `-` to make quoting a bit less onerous 
    
    $ notefile query - <<EOF
    > a = t('tag1') and not t('tag2')
    > b = g('expr1') or g('expr2') or not g('expr3')
    > a and b
    > EOF

tany and/or tall could also be used:
    
    $ notefile query "tall('a','b','c')"

Queries are pretty flexible and give a good bit of control but some actions
and queries are still better handled directly in Python.

Reminder: Do not query untrusted input!

```

# note-path


```text
usage: notefile note-path [-h] [--debug] [--note-field field] [--version]
                             [--link {source,symlink,both}] [-H] [-V]
                             [--no-hash] [--no-refresh] [--format {json,yaml}]
                             [--rewrite-format]
                             path [path ...]

positional arguments:
  path                  Specify path(s). Will print in order

optional arguments:
  -h, --help            show this help message and exit
  --link {source,symlink,both}
                        ['both'] Specify how to handle symlinks. If 'source',
                        will add the notefile to the source only (non-
                        recursively). If 'symlink', will add the notefile to
                        *just* the symlink file. If 'both', will add the
                        notefile the source (non-recursivly) and then symlink
                        to that notefile.
  -H, --hidden          Make new notes hidden. NOT default unless set with
                        $NOTEFILE_HIDDEN environment variable
  -V, --visible         Make new notes visible. Default unless set with
                        $NOTEFILE_HIDDEN environment variable
  --no-hash             Do *not* compute the SHA256 of the file. Will not be
                        able to repair orphaned notes
  --no-refresh          Do not refresh/repair file metadata when a notefile is
                        modified
  --format {json,yaml}  Note format for writing NEW notes. Will not change the
                        format for existing notes unless --rewrite-format is
                        set. Default is 'yaml' unless set with
                        $NOTEFILE_FORMAT environment variable. Currently not
                        set.
  --rewrite-format      Change to the specified format (see '--format')
                        regardless of current format.

Global Options:
  --debug               Debug mode
  --note-field field    Specify the field in the notes to read/write. Defaults
                        to 'notes' or $NOTEFILE_NOTEFIELD environment variable
  --version             show program's version number and exit

```