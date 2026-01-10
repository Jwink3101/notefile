import os, sys
import argparse
import json

# 100 --------------------------------------------------------------------------------------------->

from .nfyaml import yaml, pss, ruamel_yaml
from . import utils, debug, __version__, NOTEFIELD, HIDDEN, SUBDIR, FORMAT
from .notefile import Notefile


def cli(argv=None):
    from . import query_help

    if not argv:
        argv = sys.argv[1:]

    # Hacked commands
    if argv and argv[0] == "help":
        argv[0] = "--help"
    if argv and argv[0] == "version":
        argv[0] = "--version"

    subparsers = {}

    ## Parents:

    global_parent = argparse.ArgumentParser(add_help=False)
    global_parent_group = global_parent.add_argument_group(title="Global Options")
    global_parent_group.add_argument("--debug", action="store_true", help="Debug mode")
    global_parent_group.add_argument(
        "--note-field",
        default=NOTEFIELD,
        metavar="field",
        help="""Specify the field in the notes to read/write. Defaults to 'notes' 
                or $NOTEFILE_NOTEFIELD environment variable""",
    )
    global_parent_group.add_argument(
        "--version", action="version", version="%(prog)s-" + __version__
    )

    find_parent = argparse.ArgumentParser(add_help=False)
    find_parent_group = find_parent.add_argument_group(
        title="find Options", description="Flags for finding notes"
    )
    find_parent_group.add_argument(
        "-p",
        "--path",
        default=[],
        action="append",
        help="""Specify path(s). Can specify multiple. Directories will
                recurse and follow exclusions, etc. Specified files will not. 
                If not specified, will be '.'. If any path is specified, will ONLY
                use those paths. """,
    )
    find_parent_group.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="""Specify a glob pattern to exclude when looking for notes. Directories 
                are also matched with a trailing '/'. Can specify multiple times.""",
    )
    find_parent_group.add_argument(
        "--exclude-links", action="store_true", help="Do not include symlinked notefiles"
    )
    find_parent_group.add_argument(
        "--match-exclude-case", action="store_true", help="Match case on exclude patterns"
    )
    find_parent_group.add_argument(
        "--max-depth",
        type=int,
        metavar="N",
        default=None,
        dest="maxdepth",
        help="""Specify the maximum depth to search for notes. 
                The current directory is 0""",
    )
    find_parent_group.add_argument(
        "-x", "--one-file-system", action="store_true", help="Do not cross filesystem boundaries"
    )

    disp_parent = argparse.ArgumentParser(add_help=False)
    disp_parent_group = disp_parent.add_argument_group(
        title="Display Options",
        description="Some flags will be ignored and/or are mutually exclusive",
    )
    disp_parent_group.add_argument(
        "-0",
        "--print0",
        action="store_true",
        help="""Terminate names with a null byte. For use with `xargs -0` when 
                filenames have space""",
    )
    disp_parent_group.add_argument(
        "--export", action="store_true", help="Export notes rather than printing names or tags"
    )
    disp_parent_group.add_argument(
        "--export-format",
        choices=["yaml", "json", "jsonl"],
        default="yaml",
        help=(
            "[%(default)s] Export format. For jsonl, will be a list of dicts with the "
            "filename as '__filename' (to avoid accidentally clobbering a 'filename' key) "
            "and a metadata entry. The other formats are dictionaries"
        ),
    )
    disp_parent_group.add_argument(
        "--tag-mode",
        action="store_true",
        help="""Displays results in terms of *all* tags present in the results""",
    )
    disp_parent_group.add_argument(
        "--tag-counts",
        action="store_true",
        help="""Displays results with the counts of *all* tags present in the results. 
                Implies --tag-mode""",
    )
    disp_parent_group.add_argument(
        "--tag-count-order",
        action="store_true",
        help="""Orders the results by number of tags. Implies --tag-mode""",
    )
    disp_parent_group.add_argument(
        "-o", "--output", metavar="FILE", help="""Write results to FILE instead of stdout"""
    )
    disp_parent_group.add_argument(
        "--symlink",
        default=None,
        metavar="DIR",
        help="""Create symlinks in DIR to the found files. If used in --tag-mode, 
                will also have subdirs with the name (or filter). If there are name 
                conflicts, will add `.N` to the filename and print a warning to 
                stderr""",
    )

    search_parent = argparse.ArgumentParser(add_help=False)
    search_parent.add_argument("--all", action="store_true", help="Match for all. Default is ANY")
    # search_parent.add_argument('--any',action='store_true',help='Match for any (default)')

    search_parent_grep = search_parent.add_argument_group(
        title="grep options", description="Search for string matches"
    )
    search_parent_grep.add_argument(
        "--grep",
        action="append",
        default=[],
        metavar="expr",
        help="""Search for text. Follows python regex patterns unless --fixed-strings.
                May need to escape them for bash parsing. Can specify multiple. 
                If note contents are not strings, will use the `str()` representation""",
    )
    search_parent_grep.add_argument(
        "--fixed-strings",
        action="store_true",
        help="Match the string literally without regex patterns for grep expression",
    )
    search_parent_grep.add_argument(
        "--full-note", action="store_true", help="grep the full note, not just the notes"
    )
    search_parent_grep.add_argument(
        "--full-word",
        action="store_true",
        help=r"Matches the full word(s) of the grep expression. (adds \b)",
    )
    search_parent_grep.add_argument(
        "--match-expr-case", action="store_true", help="Match case on grep expression"
    )

    search_parent_query = search_parent.add_argument_group(
        title="query options",
        description="""Advanced Python queries. See 'query -h' for details.""",
    )
    search_parent_query.add_argument(
        "--query",
        action="append",
        default=[],
        metavar="expr",
        help="""Query expression. Can be multiple lines 
                delineated by \\n or ';' but the last line must 
                evaluate to True or False as the query. Set as `-` to read stdin""",
    )
    search_parent_query.add_argument(
        "-e",
        "--allow-exception",
        action="store_true",
        help="""Allow exceptions in the query. Still prints a warning to stderr for 
                each one""",
    )

    search_parent_tags = search_parent.add_argument_group(title="tag search options")
    search_parent_tags.add_argument(
        "-t", "--tag", action="append", default=[], help="""Specify tag to find"""
    )
    search_parent_tags.add_argument(
        "--tag-all", action="store_true", help="""Match all specified tags"""
    )

    new_parent = argparse.ArgumentParser(add_help=False)
    # new_parent.add_argument('file',help='Specify file(s)',nargs='+')

    new_parent_group = new_parent.add_argument_group(
        title="Create/Modify Options",
        description="""Flags for creating and saving notes. Not all flags 
                       are always applicable!""",
    )
    new_parent_group.add_argument(
        "--link",
        choices=[
            "source",
            "symlink",
            "both",
        ],
        default="both",
        help="""['%(default)s'] Specify how to handle symlinks. If 'source', will add 
                the notefile to the source only (non-recursively). If 'symlink', will 
                add the notefile to *just* the symlink file. If 'both', will add the 
                notefile the source (non-recursivly) and then symlink to that notefile.
            """,
    )
    new_parent_group.add_argument(
        "-H",
        "--hidden",
        action="store_true",
        default=HIDDEN,
        help="""Make new notes hidden. NOT default unless set with $NOTEFILE_HIDDEN 
                environment variable""",
    )
    new_parent_group.add_argument(
        "-V",
        "--visible",
        action="store_false",
        dest="hidden",
        help="""Make new notes visible. Default unless set with $NOTEFILE_HIDDEN 
                environment variable""",
    )
    new_parent_group.add_argument(
        "-S",
        "--subdir",
        action=argparse.BooleanOptionalAction,
        default=SUBDIR,
        help="""Make new notes in a subdir. NOT default unless set with $NOTEFILE_SUBDIR 
                environment variable. When using --subdir with --hidden, will store
                in '.notefiles' and when using --subdir with --visible, will store
                in '_notefiles'. Default %(default)s""",
    )
    new_parent_group.add_argument(
        "--no-hash",
        action="store_false",
        dest="hashfile",
        help="""Do *not* compute the SHA256 of the file. Will not be able to repair 
                orphaned notes""",
    )
    new_parent_group.add_argument(
        "--no-refresh",
        action="store_false",
        dest="refresh",
        help="Do not refresh/repair file metadata when a notefile is modified",
    )
    new_parent_group.add_argument(
        "--format",
        choices=[
            "json",
            "yaml",
        ],
        default=FORMAT,
        help="""Note format for writing NEW notes. Will not change the format
                for existing notes unless --rewrite-format is set.
                Default is 'yaml' unless set with $NOTEFILE_FORMAT
                environment variable. Currently """
        + (
            f"'{os.environ.get('NOTEFILE_FORMAT')}'."
            if "NOTEFILE_FORMAT" in os.environ
            else "not set."
        ),
    )
    new_parent_group.add_argument(
        "--rewrite-format",
        action="store_true",
        help="""Change to the specified format (see '--format')
                regardless of current format.""",
    )

    editmod_parent = argparse.ArgumentParser(add_help=False)

    editmod_parent_edit = editmod_parent.add_argument_group(
        title="Interactive Edit",
        description="Edit notes with a text editor. Other modifications come first",
    )
    editmod_parent_edit.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="Launch $EDITOR to interactivly edit the notes for a file",
    )
    editmod_parent_edit.add_argument(
        "-f",
        "--full",
        action="store_true",
        help="""Edit the full YAML file. Will always edit in YAML mode even 
                if notes are stored in JSON""",
    )
    editmod_parent_edit.add_argument(
        "-m",
        "--manual",
        action="store_true",
        help="Instead of $EDITOR, print the path and then wait for user-input to continue",
    )

    editmod_parent_edit.add_argument(
        "--tags-only", action="store_true", help="Just edit tags, not both"
    )

    editmod_parent_mod = editmod_parent.add_argument_group(
        title="Modify Notes", description="Add or replace notes. Add or remove tags"
    )
    editmod_parent_mod.add_argument(
        "-r", "--remove", default=[], action="append", metavar="TAG", help="Specify tags to remove"
    )
    editmod_parent_mod.add_argument(
        "-t", "--tag", "-a", "--add", default=[], action="append", help="Specify tags to add"
    )
    editmod_parent_mod.add_argument(
        "-R", "--replace", action="store_true", help="Replace rather than append the new note"
    )
    editmod_parent_mod.add_argument(
        "-n",
        "--note",
        action="append",
        default=[],
        help="""Notes to add (or replace). Each argument is its own line. Specify 
                `--note ""` to add empty line. Notes will come _after_ stdin if 
                applicable. Will use --note-field settings""",
    )

    # TODO Add --json

    editmod_parent_mod.add_argument(
        "-s",
        "--stdin",
        action="store_true",
        help="Read note from stdin. Prepended to any --note arguments",
    )

    repair_parent = argparse.ArgumentParser(add_help=False)
    repair_parent.add_argument(
        "path", nargs="*", action="extend", help="Additional --path arguments"
    )
    repair_parent_group = repair_parent.add_argument_group(title="Repair Options")
    repair_parent_group.add_argument(
        "--dry-run", action="store_true", help="Do not make any changes"
    )

    repair_meta_parent = argparse.ArgumentParser(add_help=False)
    repair_meta_group = repair_meta_parent.add_argument_group(title="Repair metadata options")
    repair_meta_group.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force %(prog)s to refresh all metadata (while still respecting --no-hash)",
    )

    repair_orphaned_parent = argparse.ArgumentParser(add_help=False)
    repair_orphaned_parent_group = repair_orphaned_parent.add_argument_group(
        title="Repair orphaned options", description=None
    )
    repair_orphaned_parent_group.add_argument(
        "--match",
        default=None,
        action="append",
        choices=[
            "size",
            "mtime",
            "hash",
            "name",
        ],
        help="""Specify how to search for matches. Specify multiple as needed. 'size'
                is ALWAYS implied but is the only attribute if '--match size' is the sole
                flag. Default is '--match mtime --match hash' (with '--match size' 
                implied). Specifying '--match name' means the the moved file must have the
                same name (aka leaf).
                Note: will ONLY match if there is only a single candidate so more
                requirements is also more likely to match. Use  --dry-run if needed to
                test!""",
    )
    repair_orphaned_parent_group.add_argument(
        "--search-path",
        default=[],
        action="append",
        help="""Specify path(s). Can specify multiple. Directories will
                recurse and follow exclusions, etc. Specified files will not. 
                If not specified, will be --path (or parent if a file). 
                If *any* path is specified, will ONLY use those paths and not --path""",
    )
    repair_orphaned_parent_group.add_argument(
        "--search-exclude",
        action="append",
        default=[],
        help="""Specify a glob pattern to exclude when looking for files. Directories 
                are also matched with a trailing '/'. Can specify multiple times.""",
    )
    repair_orphaned_parent_group.add_argument(
        "--search-exclude-links", action="store_true", help="Do not include symlinked files"
    )
    repair_orphaned_parent_group.add_argument(
        "--search-match-exclude-case", action="store_true", help="Match case on exclude patterns"
    )
    repair_orphaned_parent_group.add_argument(
        "--search-max-depth",
        type=int,
        metavar="N",
        default=None,
        dest="search_maxdepth",
        help="""Specify the maximum depth to search for files. 
                The current directory is 0""",
    )
    repair_orphaned_parent_group.add_argument(
        "--search-one-file-system",
        action="store_true",
        help="Do not cross filesystem boundaries when searching for a file",
    )

    parser = argparse.ArgumentParser(description="Notefile", parents=[global_parent])
    #### Subparsers

    subpar = parser.add_subparsers(
        dest="command",
        title="Commands",
        required=True,
        metavar="command",
        description="Run `%(prog)s <command> -h` for help",
    )

    subparsers["mod"] = subpar.add_parser(
        "mod",
        parents=[editmod_parent, new_parent, global_parent],
        help="Modify notes. Edit interactivly, add or replace notes, add or remove tags",
    )
    subparsers["mod"].add_argument("file", help="Specify file(s)", nargs="+")

    subparsers["edit"] = subpar.add_parser(
        "edit",
        parents=[editmod_parent, new_parent, global_parent],
        help="Shortcut for '%(prog)s mod --edit'",
    )
    subparsers["edit"].add_argument("file", help="Specify file(s)", nargs="+")

    subparsers["copy"] = subpar.add_parser(
        "copy",
        help="Copy the notes from SRC to DST(s). DST must not have any notes",
        parents=[
            new_parent,
            global_parent,
        ],
    )
    subparsers["copy"].add_argument("SRC", help="Source note")
    subparsers["copy"].add_argument(
        "DST", nargs="+", help="Destination file. Must not have ANY notes"
    )

    subparsers["replace"] = subpar.add_parser(
        "replace",
        help="Replace/Update some or all of the content in SRC to notes in DST",
        parents=[
            new_parent,
            global_parent,
        ],
    )
    subparsers["replace"].add_argument("SRC", help="Source note")
    subparsers["replace"].add_argument("DST", nargs="+", help="Destination file")
    subparsers["replace"].add_argument(
        "--field",
        action="append",
        default=None,
        help="""Specify fields to replace/update. If NONE are specified, will use
                --note-field. If ANY flag is set, will only do them. For example,
                `--field tags` will *only* replace/update tags. To do tags and notes,
                do `--field tags --field notes`. Will NOT raise any alert if field
                is not in the source""",
    )
    subparsers["replace"].add_argument(
        "--all-fields",
        action="store_true",
        help="""Ignore --fields and do all fields. This is effectively `copy` with 
                allowing it to overwrite existing notes""",
    )
    subparsers["replace"].add_argument(
        "--append",
        action="store_true",
        help="""Update/append rather than replace the contents in each field.
                With the exception of `tags`, the field values must either be
                text-based or the dest must not have anything in the field""",
    )

    subparsers["change-tag"] = subpar.add_parser(
        "change-tag",
        help="Change one tag to another (or multiple) and display the results",
        parents=[
            global_parent,
            find_parent,
            disp_parent,
            new_parent,
        ],
    )
    # ^^ Doesn't really need new_parent since will always already exist but wanted to
    #    include changing the format
    subparsers["change-tag"].add_argument("old", help="old tag to change")
    subparsers["change-tag"].add_argument("new", help="new tag(s)", nargs="+")
    subparsers["change-tag"].add_argument(
        "-n", "--dry-run", action="store_true", help="""Do not make changes"""
    )

    subparsers["vis"] = subpar.add_parser(
        "vis",
        help="Change the visibility of file(s)/dir(s)",
        parents=[global_parent, find_parent, disp_parent],
    )
    for mode in ["show", "hide"]:
        subparsers[mode] = subpar.add_parser(
            mode,
            help=f"Shortcut for '%(prog)s vis {mode}'",
            parents=[global_parent, find_parent, disp_parent],
        )

    subparsers["vis"].add_argument(
        "mode",
        choices=[
            "hide",
            "show",
        ],
        help="Visibility mode for file(s)/dir(s) ",
    )
    # Do these as a loop rather than a parent since I need to inject an argument
    # as opposed to options
    for mode in ["show", "hide", "vis"]:
        subparsers[mode].add_argument(
            "path", nargs="*", action="extend", help="Additional --path arguments"
        )
        subparsers[mode].add_argument(
            "-n", "--dry-run", action="store_true", help="""Do not make changes"""
        )
        subparsers[mode].add_argument(
            "-S",
            "--subdir",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="""
                Make new notes in a subdir. NOT default unless set with $NOTEFILE_SUBDIR 
                environment variable. When using --subdir with --hidden, will store
                in '.notefiles' and when using --subdir with --visible, will store
                in '_notefiles'. Default is based on original setting""",
        )

    subparsers["format"] = subpar.add_parser(
        "format",
        help="Change the format of file(s)/dir(s)",
        parents=[
            global_parent,
            find_parent,
            disp_parent,
        ],
    )
    subparsers["format"].add_argument(
        "format",
        choices=[
            "yaml",
            "json",
        ],
        help="Change the note format for file(s)/dir(s)",
    )
    subparsers["format"].add_argument(
        "path", nargs="*", action="extend", help="Additional --path arguments"
    )
    subparsers["format"].add_argument(
        "-n", "--dry-run", action="store_true", help="""Do not make changes"""
    )

    subparsers["repair"] = subpar.add_parser(
        "repair",
        help="Repair notefile(s): metadata and orphaned",
        parents=[
            global_parent,
            find_parent,
            new_parent,
            repair_parent,
            repair_meta_parent,
            repair_orphaned_parent,
        ],
    )
    subparsers[
        "repair",
        "m",
    ] = subpar.add_parser(
        "repair-metadata",
        help="Repair notefile(s): metadata",
        parents=[
            global_parent,
            find_parent,
            new_parent,
            repair_parent,
            repair_meta_parent,
        ],
    )
    subparsers[
        "repair",
        "o",
    ] = subpar.add_parser(
        "repair-orphaned",
        help="Repair notefile(s): orphaned",
        parents=[
            global_parent,
            find_parent,
            new_parent,
            repair_parent,
            repair_orphaned_parent,
        ],
    )

    ## Single item see
    subparsers["cat"] = subpar.add_parser("cat", help="Print the note", parents=[global_parent])
    subparsers["cat"].add_argument("file", help="Specify file to cat")
    subparsers["cat"].add_argument(
        "-f",
        "--full",
        action="store_true",
        help="Display the full YAML note rather than just the note text",
    )
    subparsers["cat"].add_argument("-t", "--tags", action="store_true", help="Display the tags")

    ## Multi-item search and/or see
    subparsers["find"] = subpar.add_parser(
        "find",
        help="Find and list all notes",
        parents=[
            global_parent,
            find_parent,
            disp_parent,
        ],
    )
    subparsers["find"].add_argument(
        "--orphaned",
        action="store_true",
        help=("Find orphaned notes only. Does not repair. See repair-orphaned to repair"),
    )

    subparsers["export"] = subpar.add_parser(
        "export",
        help=(
            "Shortcut for '%(prog)s find --export'. "
            "Note, can use '%(prog)s search --export <search flags>' if needed "
            "with search queries."
        ),
        parents=[
            global_parent,
            find_parent,
            disp_parent,
        ],
    )
    subparsers["export"].add_argument(
        "path", nargs="*", action="extend", help="Additional --path arguments"
    )

    subparsers["search"] = subpar.add_parser(
        "search",
        help="Find and list all notes with criteria",
        parents=[
            global_parent,
            find_parent,
            search_parent,
            disp_parent,
        ],
    )

    subparsers["grep"] = subpar.add_parser(
        "grep",
        help="Shortcut for '%(prog)s search --grep'",
        parents=[
            global_parent,
            find_parent,
            search_parent,
            disp_parent,
        ],
    )
    subparsers["grep"].add_argument(
        "grep", nargs="*", action="extend", help="Additional --grep expressions"
    )

    subparsers["query"] = subpar.add_parser(
        "query",
        help="""Shortcut for '%(prog)s search --query'. Also has additional details 
                on queries""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=query_help(print_help=False),
        parents=[
            global_parent,
            find_parent,
            search_parent,
            disp_parent,
        ],
    )
    subparsers["query"].add_argument(
        "query", nargs="*", action="extend", help="""Additional queries added to any --query."""
    )

    subparsers["tags"] = subpar.add_parser(
        "tags",
        help="Shortcut for '%(prog)s search --tag-mode --tag'",
        parents=[
            global_parent,
            find_parent,
            search_parent,
            disp_parent,
        ],
    )
    subparsers["tags"].add_argument("tag", nargs="*", action="extend")

    # Path
    subparsers["note-path"] = subpar.add_parser(
        "note-path",
        help="""Return the path to the notefile (or potential file if the note doesn't
                yet exist)""",
        parents=[
            global_parent,
            new_parent_group,
        ],
    )
    subparsers["note-path"].add_argument(
        "path", nargs="+", help="Specify path(s). Will print in order"
    )

    args = parser.parse_args(argv)

    global DEBUG
    if args.debug:
        DEBUG = True
    else:  # reset by environ
        DEBUG = os.environ.get("NOTEFILE_DEBUG", "").strip().lower() == "true"

    if DEBUG:  # May have been set not at CLI
        debug("argv: {}".format(repr(argv)))
        debug(args)

    try:
        if args.command in {"edit", "mod"}:
            SingleMod(args)
        elif args.command in {"copy", "replace"}:
            CopyReplace(args)
        elif args.command == "change-tag":
            ChangeTag(args)
        elif args.command == "format":
            FormatChangeCLI(args)
        elif args.command in {"vis", "show", "hide"}:
            if args.command != "vis":
                args.mode = args.command
            VisChangeCLI(args)
        elif args.command == "cat":  # no need to call an object
            note = Notefile(args.file, note_field=args.note_field)
            print(note.cat(tags=args.tags, full=args.full))
        elif args.command in {"find", "export", "search", "grep", "query", "tags"}:
            args.tag = set(getattr(args, "tag", []))
            if args.command == "tags":
                args.tag_mode = True
            if args.command == "export":
                args.export = True

            tagkeys = ["tag_mode", "tag_counts", "tag_count_order"]
            args.tag_mode = any(getattr(args, k, False) for k in tagkeys)

            SearchCLI(args)
        elif args.command in {"repair", "repair-metadata", "repair-orphaned"}:
            RepairCLI(args)
        elif args.command == "note-path":
            NotePathCLI(args)
    except Exception as E:
        if DEBUG:
            raise
        print(f"ERROR: {E}", file=sys.stderr)
        sys.exit(1)


################## Currently undocumented...
nproc = os.environ.get("NOTEFILE_PAR", "1")
if nproc.strip().lower() == "all":
    nproc = os.cpu_count()
if int(nproc) > 1:
    import multiprocessing as mp

    def _r(note):
        return note.read()

    def noteread(notes):
        with mp.Pool() as pool:
            yield from pool.imap_unordered(_r, notes, chunksize=100)

else:

    def noteread(notes):
        """Just call read. But may get parallel in the future"""
        for note in notes:
            yield note.read()


################## /Currently undocumented...


class BaseCLI:
    def find(self, **kwargs):
        args = self.args
        from . import find

        noteopts = kwargs.pop("noteopts", {})
        noteopts["note_field"] = args.note_field
        yield from find(
            path=args.path,
            excludes=args.exclude,
            matchcase=args.match_exclude_case,
            maxdepth=args.maxdepth,
            one_file_system=args.one_file_system,
            exclude_links=args.exclude_links,
            noteopts=noteopts,
            **kwargs,
        )

    @property
    def noteopts(self):
        args = self.args
        return dict(
            hidden=args.hidden,
            subdir=args.subdir,
            link=args.link,
            hashfile=args.hashfile,
            note_field=args.note_field,
            format=args.format,
            rewrite_format=args.rewrite_format,
        )

    @property
    def outbuffer(self):
        if not hasattr(self, "_outbuffer"):
            if self.args.output:
                self._outbuffer = open(self.args.output, "wb")
            else:
                self._outbuffer = sys.stdout.buffer
        return self._outbuffer


class DisplayMIXIN:
    """For displaying notes"""

    def display_dispatch(self, notes):
        if self.args.export:
            self.export(notes)
        elif self.args.tag_mode:
            self.display_tags(notes)
        else:
            self.display(notes)

    def display(self, notes):
        """Display for non-tag modes. This will display as returned"""
        sep = b"\x00" if self.args.print0 else b"\n"
        for note in notes:
            try:
                self.outbuffer.write(note.names0.filename.encode() + sep)
            except:
                print(f"{note.names0.filename = }")
                raise
            self.outbuffer.flush()

            if self.args.symlink:
                utils.symlink_file(note.names0.filename, self.args.symlink)

    def display_tags(self, notes):
        """
        Display for tag modes.
        This will have to wait for the notes iterator to finish
        """
        from collections import defaultdict

        tags = defaultdict(list)

        for note in notes:
            for tag in note.data.tags:
                tags[tag].append(note.names0.filename)

        if not tags:
            return

        counts = {tag: len(notes) for tag, notes in tags.items()}
        if self.args.tag_count_order:
            tagorder = sorted(tags, key=lambda tag: (counts[tag], tag), reverse=True)
        else:
            tagorder = sorted(tags)

        # Build the result dict. We use py3.8+ so we can assume the order here
        resdict = {}
        for tag in tagorder:
            if self.args.tag_counts:
                resdict[tag] = counts[tag]
            else:
                resdict[tag] = sorted(tags[tag], key=str.lower)

        yaml.dump(resdict, self.outbuffer)
        self.outbuffer.flush()

        if self.args.symlink:
            for tag, notes in tags.items():
                dirdest = os.path.join(self.args.symlink, tag)
                for note in notes:
                    utils.symlink_file(note, dirdest)

    def export(self, notes):
        res = {"__comment": None}
        res["description"] = "notefile export"
        res["time"] = utils.now_string()
        res["notefile version"] = __version__
        if self.args.export_format in ["yaml", "json"]:
            res["notes"] = {}
            for note in notes:
                res["notes"][note.names0.filename] = note.data

            if self.args.export_format == "yaml":
                del res["__comment"]
                res = pss(res)
                res = ruamel_yaml.comments.CommentedMap(res)
                res.yaml_set_start_comment("YAML formatted notefile export")

                yaml.dump(res, self.outbuffer)
            else:
                res["__comment"] = "YAML formatted notefile export"
                dump = json.dumps(res, indent=1, ensure_ascii=False)
                self.outbuffer.write(dump.encode("utf8"))  # Needs to be bytes so two step
        else:
            res["__comment"] = "json lines formatted notefile export"

            meta = json.dumps(res, ensure_ascii=False)
            self.outbuffer.write(meta.encode("utf8") + b"\n")

            for note in notes:
                row = {"__filename": note.names0.filename}
                row.update(note.data)
                row = json.dumps(row, ensure_ascii=False)
                self.outbuffer.write(row.encode("utf8") + b"\n")
                self.outbuffer.flush()


class SearchCLI(DisplayMIXIN, BaseCLI):
    def __init__(self, args):
        self.args = args

        orphaned = getattr(self.args, "orphaned", False)

        # Build the pipeline. Do not read for find. Do not query for export.
        notes = self.find(include_orphaned=orphaned)
        if orphaned:
            notes = (note for note in notes if note.orphaned)

        if args.command != "find":  # no need to read if not testing or exporting
            notes = noteread(notes)  # May be parallel in the future
            if args.command != "export":
                # Read stdin on query if -
                args.query = [
                    q if q != "-" else sys.stdin.read().strip() for q in getattr(args, "query", [])
                ]
                # Process. Do the query
                notes = (note for note in notes if self.test(note))

        self.display_dispatch(notes)

    def test(self, note):
        """
        Test the note based on the conditions
        """
        args = self.args

        grepopts = dict(
            matchcase=args.match_expr_case,
            full_note=args.full_note,
            full_word=args.full_word,
            fixed_strings=args.fixed_strings,
            match_any=not args.all,
        )

        m = False  # whether we did anything
        if args.grep:
            t = note.grep(args.grep, **grepopts)
            if args.all and not t:
                return False  # short circuit
            elif not args.all and t:
                return True
            m = True
        if args.query:
            t = note.query(args.query, allow_exception=args.allow_exception, **grepopts)
            if args.all and not t:
                return False  # short circuit
            elif not args.all and t:
                return True
            m = True
        if args.tag:
            tags = set(t.lower() for t in note.data.tags)
            if args.tag_all:
                t = len(args.tag - tags) == 0
            else:
                t = len(args.tag.intersection(tags)) > 0
            if args.all and not t:
                return False  # short circuit
            elif not args.all and t:
                return True
            m = True

        # At this point, we either hit them all with ALL, we hit none with ANY,
        # or didn't have a query
        return args.all or not m


class SingleMod(BaseCLI):
    def __init__(self, args):
        self.args = args

        if self.args.command == "edit":
            self.args.edit = True

        if not (args.edit or args.tag or args.remove or args.note or args.stdin):
            raise ValueError(
                "Must specify at least one of --edit, --tag, --remove, --note, --stdin"
            )
        addnote = [sys.stdin.read().strip()] if args.stdin else []
        args.addnote = "\n".join(addnote + args.note)
        self.editmod()

    def editmod(self):
        args = self.args
        for file in args.file:
            note = Notefile(file, **self.noteopts)

            note.modify_tags(add=args.tag, remove=args.remove)
            note.add_note(args.addnote, replace=args.replace)  # also does strip()
            if args.edit:
                note.interactive_edit(full=args.full, manual=args.manual, tags_only=args.tags_only)

            if args.refresh:
                note.repair_metadata(force=False)

            note.write()


class CopyReplace(BaseCLI):
    def __init__(self, args):
        self.args = args
        src = Notefile(args.SRC, **self.noteopts)

        if args.command == "copy":
            opts = dict(allfields=True, newonly=True, append=False)
        else:
            opts = dict(
                fields=args.field, allfields=args.all_fields, newonly=False, append=args.append
            )

        for dst in args.DST:
            src.replaceto(dst, noteopts=self.noteopts, **opts)


class ChangeTag(DisplayMIXIN, BaseCLI):
    def __init__(self, args):
        self.args = args

        self.old = args.old.lower().strip()
        self.new = [t.lower().strip() for t in args.new]

        if args.dry_run:
            self.outbuffer.write(b"# DRY RUN\n")
            self.outbuffer.flush()

        notes = self.find()
        notes = noteread(notes)
        notes = (self.change(note) for note in notes)
        notes = (note for note in notes if note is not None)

        self.display_dispatch(notes)

    def change(self, note):
        tags = set(t.lower() for t in note.data["tags"])
        if self.old in tags:
            if self.args.dry_run:
                return note
            return note.modify_tags(add=self.new, remove=self.old).write()


class VisChangeCLI(DisplayMIXIN, BaseCLI):
    def __init__(self, args):
        self.args = args
        if args.dry_run:
            self.outbuffer.write(b"# DRY RUN\n")
            self.outbuffer.flush()

        notes = self.find()
        notes = (
            note
            for note in notes
            if note.change_visibility_subdir(
                mode=args.mode, subdir=args.subdir, dry_run=args.dry_run
            )
        )
        self.display_dispatch(notes)

    # Because we do not need to otherwise read the notes
    # need to do it here. It's a waste but oh well!
    def display_tags(self, notes):
        notes = noteread(notes)
        return super().display_tags(notes)


class FormatChangeCLI(DisplayMIXIN, BaseCLI):
    def __init__(self, args):
        self.args = args

        if args.dry_run:
            self.outbuffer.write(b"# DRY RUN\n")
            self.outbuffer.flush()

        notes = self.find(noteopts=dict(format=args.format, rewrite_format=True))
        notes = noteread(notes)
        notes = (note for note in notes if note.format != note.format0)
        if not args.dry_run:
            # Force writing. Prev set rewrite_format=True!
            notes = (note.write(force=True) for note in notes)
        self.display_dispatch(notes)

    # Because we do not need to otherwise read the notes need to do it here.
    # It's a waste but oh well! (Could be done in the display but this can be
    # vectorized in the future)
    def display_tags(self, notes):
        notes = noteread(notes)
        return super().display_tags(notes)


class RepairCLI(BaseCLI):
    def __init__(self, args):
        self.args = args
        if args.command in {"repair", "repair-metadata"}:
            self.repair_metadata()
        if args.command in {"repair", "repair-orphaned"}:
            self.repair_orphaned()

    def repair_metadata(self):
        args = self.args

        notes = self.find(noteopts=self.noteopts, include_orphaned=False)
        notes = noteread(notes)
        for note in notes:
            if note.orphaned:
                continue  # can happen iff path is DIRECTLY specified
            if note.repair_metadata(dry_run=args.dry_run, force=args.force_refresh):
                note.write()
                print(f'repaired{" (DRY-RUN)" if args.dry_run else ""}: {note.names0.filename}')

    def repair_orphaned(self):
        args = self.args
        notes = self.find(noteopts=self.noteopts, include_orphaned=True)
        notes = (note for note in notes if note.orphaned)
        notes = noteread(notes)

        match = set(args.match) if args.match else {"mtime", "hash"}

        mtime = "mtime" in match
        filehash = "hash" in match
        name = "name" in match

        p = "(DRY RUN) " if args.dry_run else ""

        if not args.search_path:
            for p in args.path:
                if not p:
                    continue
                args.search_path.append(p if os.path.isdir(p) else os.path.dirname(p))

        for note in notes:
            r = note.repair_orphaned(
                mtime=mtime,
                filehash=filehash,
                name=name,
                dry_run=args.dry_run,
                search_path=args.search_path,
                search_excludes=args.search_exclude,
                search_matchcase=args.search_match_exclude_case,
                search_maxdepth=args.search_maxdepth,
                search_one_file_system=args.search_one_file_system,
                search_exclude_links=args.search_exclude_links,
            )
            if r:
                print(f"{p}{note.destnote0} --> {r}")


class NotePathCLI(BaseCLI):
    def __init__(self, args):
        self.args = args
        for path in args.path:
            print(Notefile(path, **self.noteopts).destnote0, flush=True)
