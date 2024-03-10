from . import HIDDEN, SUBDIR, NOTEFIELD, NOHASH, NOTESEXT, debug, warn, __version__, DT, FORMAT
from .nfyaml import pss, load_yaml, ruamel_yaml, yaml, yamltxt
from .utils import now_string, Bunch, sha256, tmpfileinpath, flattenlist, normalize_tags
from . import find

from pathlib import Path
import shlex
import sys, os, io
import json
import copy
import shutil
import functools

METADATA = frozenset(("filesize", "mtime", "sha256", "last-updated", "notefile version"))

_TESTEDIT = False  # Only used in testing


class Notefile:
    """
    Main notes object

    Inputs:
    -------
    filename
        Filename (or notefile name). Will be set as needed

    hidden [environment variable $NOTEFILE_HIDDEN otherwise False]
        Whether or not to *prefer* the hidden notefile

    subdir [environment variable $NOTEFILE_SUBDIR otherwise False]
        Whether or not to *prefer* the subdir notefile

    format [environment variable $NOTEFILE_FORMAT otherwise 'yaml']
        Specify 'yaml' or 'json' for output format. Note that the extensions
        will always be .yaml since yaml is a superset of JSON

    rewrite_format [False]
        Whether to change the format to `format` regardless of current format.

    link ['both']
        How to handle symlinks.

    hashfile [True]
        Whether or not to hash the file

    note_field [NOTEFIELD]
        The field for reading and writing notes

    Notable Attributes:
    -------------------
    Any attribute with 0 is the original. The version without 0 is the refferent
    if the file is a symlink and not 'symlink' mode

    filename0, filename: str
        File being noted

    destnote0, destnote: str
        The final note location.

    islink: bool
        Whether or not the note is a link.

    hidden: bool
        Whether the note is hidden or not. May be different than the setting
        if the note already existed

    data:
        Note data including 'notes' and 'tags'. If called, will automatically read()
        the note.

    Notable Methods:
    ---------------
    read()
        Read the contents of the note. Done automatically when accessing self.data

    writes()
        Return a YAML string

    write()
        Write the note content. Many actions will change data but will not save
        it unless write() is called

    make_links()
        Build the appropriate symlinks if the note is a link

    isempty()
        Whether or not it is empty. Looks at ALL fields besides metadata

    Note:
    -----
    Most methods also return itself for convenience
    """

    def __init__(
        self,
        filename,
        hidden=HIDDEN,
        subdir=SUBDIR,
        format=FORMAT,
        rewrite_format=False,
        link="both",
        hashfile=True,
        note_field=NOTEFIELD,
    ):
        ## Notation:
        #   _0 names re the original file for a link (or when 'symlink' mode).
        #   When not a link, it doesn't matter!
        self.hashfile = hashfile
        self.link = link
        self.note_field = note_field
        # _0 is specified format. NOT actual format which will get reset
        self.format = self.format0 = format.lower()
        self.rewrite_format = rewrite_format
        self.names = self.names0 = get_filenames(filename)

        if os.path.basename(self.names0.filename).startswith("."):
            warn(f"hidden files may not always work: {repr(self.names.filename)}")

        # Store the original paths. Will be reset later if link
        #         self.destnote0, *_ = hidden_chooser(self.names, hidden=hidden, subdir=subdir)
        self.destnote0, self.exists0, self.is_hidden0, self.is_subdir0 = hidden_chooser(
            self.names, hidden=hidden, subdir=subdir
        )

        ## Handle links. If both or source, reset to the referent if the link
        # mode cannot be deduced. If it can, use that!
        if not link in {"both", "symlink", "source"}:
            raise ValueError("'link' must be in {'both','symlink','source'}")

        # Be False even if link for 'symlink' mode
        self.islink = os.path.islink(self.names.filename) and link in {"both", "source"}

        if self.islink:
            # Edge Case: Note created in symlink mode but isn't being modified
            # as such. Change to that
            if os.path.isfile(self.destnote0) and not os.path.islink(self.destnote0):
                warn(
                    f"Linked file ({repr(self.names0.filename)}) has conflicting notes. "
                    "Changing to 'symlink' mode"
                )
                self.islink = False
                self.link == "symlink"
            else:
                self.dest0 = os.readlink(self.names.filename)
                dest = os.path.join(os.path.dirname(self.names.filename), self.dest0)
                self.names = get_filenames(dest)  # reset this

                debug(f"Linked Note: {repr(self.names.filename)} --> {repr(self.dest0)}")

        # Get the actual notefile path (destnote) regardless of hidden settings
        # And whether it exists
        self.destnote, self.exists, self.is_hidden, self.is_subdir = hidden_chooser(
            self.names, hidden=hidden, subdir=subdir
        )
        self.hidden, self.subdir = hidden, subdir  # Settings may not be reality

        self.filename = self.names.filename
        self.filename0 = self.names0.filename

        # Check if orphhaned on original file (broken links are still NOT orphaned)
        self.orphaned = not exists_or_link(self.names0.filename)

        self.txt = None
        self._data = None
        self._write_count = 0

    def read(self, _sha256=None):
        """
        Read the note and store the data.
        """
        if self.exists:
            debug("loading {}".format(self.destnote))
            try:
                self.txt = Path(self.destnote).read_text()
            except FileNotFoundError:
                self.txt = self._read_from_broken_link_from_hide()
            try:
                self._data = json.loads(self.txt)
                self.format = "json"
            except json.JSONDecodeError:
                self._data = load_yaml(self.txt)
                self.format = "yaml"

            self._data.pop("__comment", None)
        else:
            debug("New notefile")
            self._data = {}
            try:
                stat = os.stat(self.names.filename)

                self._data["filesize"] = stat.st_size
                self._data["mtime"] = stat.st_mtime
                if self.hashfile:
                    self._data["sha256"] = sha256(self.names.filename)
                self.txt = self.writes()
            except Exception as E:
                if os.path.islink(self.names0.filename):
                    warn(
                        f"{repr(self.names0.filename)} is a broken link to {repr(self.names.filename)}."
                    )
                    self._data["filesize"] = -1
                    self._data["mtime"] = -1
                else:
                    raise  # Not sure what causes this

        if "tags" not in self._data:
            self._data["tags"] = []

        # Because we write with ruamel_yaml using YAML 1.2 and read (if possible)
        # with PyYAML (1.1), tags "yes" and "no" get converted to True and False.
        # Fix this edge case for now
        t = []
        for tag in self._data["tags"]:
            if tag is True:
                tag = "yes"
            if tag is False:
                tag = "no"
            t.append(tag)
        self._data["tags"][:] = normalize_tags(t)

        if self.note_field not in self._data:
            self._data[self.note_field] = ""
        self._data = Bunch(**self._data)

        # Make a copy for compare later. Use deep copy in case mutable
        # objects are modified
        self._data0 = copy.deepcopy(self._data)

        return self  # for convenience

    @property
    def data(self):
        if not self._data:
            debug("Automatic read()")
            self.read()
        return self._data

    @data.setter
    def data(self, data):
        debug("data setter")
        self._data = data

    def writes(self, format=None):
        """
        Return a string of the notes.

        If format is None, will use default. Otherwise, it can be set with a format
        """
        if self.note_field in self.data and isinstance(self.data[self.note_field], str):
            self.data[self.note_field] = self.data[self.note_field].strip()

        tags = self.data.get("tags", [])
        tags = set(t.strip() for t in tags if t.strip())
        self.data["tags"] = sorted(tags)

        data = pss(self.data)  # Will recurse into lists and dicts too
        data["last-updated"] = now_string()
        data["notefile version"] = __version__

        if not format:
            format = self.format0 if self.rewrite_format else self.format

        if format.lower() not in {"json", "yaml"}:
            warn(f"Unsupported format '{self.format}'. Using 'yaml'")

        if format.lower() == "json":
            _d = {"__comment": f"JSON Formatted notes created with notefile version {__version__}"}
            _d.update(data)
            return json.dumps(_d, indent=1, ensure_ascii=False)
        else:  # the default
            data = ruamel_yaml.comments.CommentedMap(data)
            data.yaml_set_start_comment(
                f"YAML Formatted notes created with notefile version {__version__}"
            )

            with io.StringIO() as stream:
                yaml.dump(data, stream)
                debug(f"yaml dumped {self.destnote}")
                return stream.getvalue()

    dumps = writes

    def write(self, force=False):
        """
        Write the data and also (re)set

        Inputs:
        -------
        force [False]
            Make it write even if it hasn't been modified
        """

        if not force and not self.ismod():
            debug("Note not modified. Not saving")
            self.make_links()  # Rebuild the links in case they were broken
            return self

        txt = self.txt = self.writes()

        # Make the write atomic
        tmpfile = Path(self.destnote).with_suffix(".yaml.swp")
        tmpfile.parent.mkdir(exist_ok=True, parents=True)
        tmpfile.write_text(txt)
        tmpfile.rename(self.destnote)
        debug(f"Wrote {self.destnote}")

        self.make_links()

        self._write_count += 1
        self.exists = True
        return self  # for convenience

    save = dump = write

    def replaceto(
        self, dst, fields=None, allfields=False, noteopts=None, newonly=False, append=False
    ):
        """
        Replace the `fields` of dst with those of current note.

        Options:
        --------
        dst
            Destination note.

        fields [None]
            If None, will *just* be the `self.notefield`. If *anything* is specified will
            ONLY be those. For example, setting `fields='tags'` will only update tags. To
            update notes too, do `fields=('tags','notes')`

            Will NOT raise a warning if field is not in the source

        allfields [False]
            Ignore the above and do all fields. This is effectively `copyto()` with
            allowing it to overwrite existing notes.

        noteopts [None]
            Options for the destination note if it is new

        newonly [False]
            If True, dst must NOT have a note

        append [False]
            If True, update/append rather than replace the contents in each field.
            With the exception of `tags`, the field values must either be text-based
            or the dest must not have anything in the field

        """
        if noteopts is None:
            noteopts = {}

        if fields is None:
            fields = [self.note_field]

        if isinstance(fields, str):
            fields = [fields]

        if allfields:
            fields = set(self.data)

        dst_note = Notefile(dst, **noteopts)
        if newonly and (exists_or_link(dst_note.destnote0) or exists_or_link(dst_note.destnote)):
            raise ValueError("Dest cannot have a note already")

        dst_note.read()

        for field in fields:
            if field in METADATA or field not in self.data:
                continue

            # Need to handle appends iff string data or tags. But if the dst is new
            # and therefore doesn't have any non-standard fields, allow it to still
            # work in append mode. Allow field to exist in dest but be empty
            if not append or not dst_note.data.get(field, None):  # Just replace
                dst_note.data[field] = self.data[field]
                continue

            # Try appending. Handle tags but otherwise, try to join strings and catch
            # the error
            if field == "tags":
                curr_tags = normalize_tags(self.data.get("tags", []), sort=False)
                dest_tags = normalize_tags(dst_note.data.get("tags", []), sort=False)
                dst_note.data["tags"] = sorted(curr_tags.union(dest_tags))
                continue

            try:
                curr_field = self.data[field]
                dest_field = dst_note.data.get(field, "")
                joined = "\n".join([dest_field, curr_field]).lstrip()
                if joined:
                    dst_note.data[field] = joined
            except TypeError:
                raise TypeError("Cannot append when fields exist and are not strings")

        dst_note.write()
        return dst_note

    copyto = functools.partialmethod(replaceto, newonly=True, allfields=True)

    def ismod(self):
        """
        Compare data0 (when read()) to data (before write())
        """
        # Will do a dictionary compare at the end so pop() certain keys before
        # we get to that. Since we're removing then, make a copy
        if not hasattr(self, "data0"):
            return True

        old, new = (self.data0.copy(), self.data.copy())

        for key in ["last-updated", "notefile version"]:
            old.pop(key, None)
            new.pop(key, None)

        # In the future, allow for no mtime test
        if abs(old.pop("mtime", 0) - new.pop("mtime", 99999999)) >= DT:
            return True  # The file has been modified. Always do this

        # Make tags comparison based on sets
        old["tags"] = normalize_tags(old.get("tags", []), sort=False)
        new["tags"] = normalize_tags(new.get("tags", []), sort=False)

        return not old == new

    def make_links(self):
        """
        Build the links if the note is a link.
        """
        # Handle both-type links by linking to the note
        if self.islink and self.link == "both":
            linknote = self.destnote0  # Original path for the note
            linkpath = os.path.join(os.path.dirname(self.dest0), os.path.basename(self.destnote))
            try:
                os.remove(linknote)
            except OSError:
                pass

            os.symlink(linkpath, linknote)

    def interactive_edit(self, full=False, manual=False, tags_only=False):
        """Launch the editor. Does *NOT* write()"""
        import subprocess, shlex

        editor_names = ["EDITOR", "GIT_EDITOR", "SVN_EDITOR", "LOCAL_EDITOR"]
        for editor_name in editor_names:
            try:
                editor = os.environ[editor_name]
                break
            except KeyError:
                pass
        else:
            raise ValueError(
                "Must specify an editor. Possible enviorment variables: "
                + ", ".join("'{}'".format(e) for e in editor_names)
            )

        tagtxt = "<< Comma-seperated tags. DO NOT MODIFY THIS LINE >>"
        info = "# filename: {}\n# notedest: {}".format(self.names.filename, self.destnote)

        tags = normalize_tags(self.data.get("tags", []))
        tags = ", ".join(tags)

        if full:
            txt = self.writes(format="yaml")
            content = txt + "\n" + info
        elif tags_only:
            content = tags + "\n\n# Comma-seperated tags\n" + info
        else:
            content = self.data.get(self.note_field, "")  # in case it's a dict
            if not isinstance(content, str):
                raise TypeError("Cannot edit non-string notes. Edit the full YAML instead")
            content += "\n\n" + tagtxt + "\n"

            content += tags + "\n" + "\n" + info + "\n"

        tmpfile = tmpfileinpath(self.destnote) + (".yaml" if full else ".txt")
        Path(tmpfile).parent.mkdir(exist_ok=True, parents=True)
        with open(tmpfile, "wt") as file:
            file.write(content)

        if _TESTEDIT:  # This is ONLY used in testing.
            with open(tmpfile, "wt") as file:
                file.write(str(_TESTEDIT))
        elif manual:
            input(f"Edit and save: {repr(tmpfile)}\nPress any key to continue ")
        else:
            subprocess.check_call(shlex.split(editor) + [tmpfile])

        with open(tmpfile, "rt") as f:
            newtxt = f.read()
        os.unlink(tmpfile)

        if full:
            self._data = Bunch(**load_yaml(newtxt))
        else:
            lines = iter(newtxt.strip().split("\n"))
            note = []
            tags = []

            if not tags_only:  # Read notes first
                for line in lines:  # Get notes
                    if line.strip() == tagtxt:
                        break
                    note.append(line)
                self.data[self.note_field] = "\n".join(note)  # Only if modifying notes

            for line in lines:  # Get tags with the remaining lines
                if line.startswith("# filename: ") or line.startswith("# Comma-"):
                    break
                tags.extend(line.split(","))

            self.data["tags"] = normalize_tags(tags)

        return self  # for convenience

    def add_note(self, note, replace=False):
        """Add (or replace) a note. Does *NOT* write()"""
        if note is None:
            note = ""

        if replace:
            self.data[self.note_field] = note
        else:
            if not isinstance(self.data[self.note_field], str):
                raise TypeError("Cannot modify non-string notes. Use with replace")
            self.data[self.note_field] += "\n" + note
        self.data[self.note_field] = self.data[self.note_field].strip()

        return self  # for convenience

    def modify_tags(self, add=tuple(), remove=tuple()):
        """
        Add or remove tags. Does *NOT* write().

        Inputs:
        -------
        add [empty tuple]
            Iterable or str of tags to add

        remove [empty tuple]
            Iterable or str of tags to remove

        """
        tags = self.data.get("tags", [])
        tags = normalize_tags(tags, sort=False)  # set of tags

        add = normalize_tags(add, sort=False)  # also handles strings
        remove = normalize_tags(remove, sort=False)  # also handles strings

        self.data["tags"] = normalize_tags(tags.union(add).difference(remove))

        return self  # for convenience

    def change_visibility_subdir(self, *, mode=None, subdir=None, dry_run=False):
        """
        Change the visibility to 'hide' or 'show'

        Inputs:
        -------
        mode [None]
            Specify 'hide' or 'show' to set it or None to keep as is.

        subdir [None]
            Specify True or False to set it or None to keep it as is.

        dry_run [False]
            If True, do not make the change

        Returns:
        --------
        True if mode changed or False
        """
        if mode is None:
            mode = "hide" if self.is_hidden else "show"
        if subdir is None:
            subdir = self.is_subdir
        newnames = get_filenames(self.names0.filename)
        desired_destnote = {  # (hidden,subdir)
            (True, True): newnames.hsubdir,
            (True, False): newnames.hidden,
            (False, True): newnames.vsubdir,
            (False, False): newnames.visible,
        }[mode == "hide", subdir]

        if desired_destnote == self.destnote0:
            return False  # Do nothing

        if os.path.exists(desired_destnote):
            warn(
                f"Both source and dest notes exist for {repr(self.names.filename)}. Not changing mode"
            )
            return False

        if dry_run:
            return True

        Path(desired_destnote).parent.mkdir(exist_ok=True, parents=True)
        try:
            shutil.move(self.destnote0, desired_destnote)
        except (OSError, IOError) as E:
            warn(f"Error on move '{src_note}' to '{dst_note}'. Error: {E}")

        # Change attributes for this now
        self.is_hidden = mode == "hide"
        self.is_subdir = subdir
        self.destnote0 = desired_destnote  # Using the 0 above

        return True

    def cat(self, tags=False, full=False):
        """cat the notes to a string"""
        if full:
            return self.writes()

        if tags:
            tags = normalize_tags(self.data.get("tags", []))
            return "\n".join(tags)

        txt = self.data.get(self.note_field, "")
        if not isinstance(txt, str):
            warn("Non-string note. Converting to YAML")
            txt = yamltxt(txt)
        return txt

    def isempty(self):
        for key in set(self.data) - METADATA:
            if self.data[key]:
                return False

        return True

    def repair_metadata(self, dry_run=False, force=False):
        """
        Repair (if Needed) the notefile metadata.

        If force, will check (mtime,size) and reset as needed.
        Otherwise, will first check (mtime,size). If they are wrong, will update
        them and the sha256 if self.hashfile

        dry_run will *not* update anything

        does *NOT* write!
        """
        # This is designed to be called before reading, etc for orphaned
        if not os.path.exists(self.names.filename):
            warn(f"File {repr(self.names.filename)} is orphaned or link is broken")
            return

        stat = os.stat(self.names.filename)

        if not dry_run and (self._isbroken_broken_from_hide() or force):
            self.make_links()

        if (
            force
            or self.data.get("filesize", -1) != stat.st_size
            or abs(self.data.get("mtime", -1) - stat.st_mtime) > DT
        ):
            if dry_run:
                return True  # Do not do anything else since we won't be writing

            self.data["filesize"] = stat.st_size
            self.data["mtime"] = stat.st_mtime
            if self.hashfile:
                self.data["sha256"] = sha256(self.names.filename)

            return True

        return False

    def repair_orphaned(
        self,
        mtime=True,
        filehash=True,
        name=False,
        dry_run=False,
        search_path=".",
        search_excludes=None,
        search_matchcase=False,
        search_maxdepth=None,
        search_one_file_system=False,
        search_exclude_links=False,
    ):
        """
        Repair orphaned (file moved).

        Always searches by filesize but can also look for matches by mtime, filehash,
        and/or name (i.e. leaf node).

        Searches from `search_path` with NO EXCLUSIONS.

        return the new dest or None
        """
        from .find import find

        if filehash and len(self.data.get("sha256", "")) != 64:  # not a computed hash
            warn(f"Cannot repair {self.names.filename} based on hash since it's missing")
            return

        files = find(
            path=search_path,
            excludes=search_excludes,
            matchcase=search_matchcase,
            maxdepth=search_maxdepth,
            one_file_system=search_one_file_system,
            exclude_links=search_exclude_links,
            filemode=True,
        )

        basename = os.path.basename(self.names0.filename)

        candidates = []
        for file in files:
            # do the tests in order of simplicity to compute
            if name and basename != os.path.basename(file):
                continue  # save the stat call

            try:
                stat = os.stat(file)
            except FileNotFoundError:
                continue  # likely a broken link

            if stat.st_size != self.data.filesize:
                continue
            if mtime and abs(self.data.mtime - stat.st_mtime) > DT:
                continue
            if filehash and self.data["sha256"] != sha256(file):
                continue

            candidates.append(file)
        if len(candidates) > 1:
            wtxt = f"{len(candidates)} candidates found for '{self.destnote0}'. Not repairing"
            wtxt += "\n   ".join([""] + candidates)
            warn(wtxt)
            return

        elif len(candidates) == 0:
            warn(f"No match for '{self.destnote0}'")
            return

        newfile = candidates[0]

        names = get_filenames(newfile)
        newnote, *_ = hidden_chooser(names, hidden=self.is_hidden, subdir=self.is_subdir)
        if os.path.exists(newnote):
            warn(f"Notefile exists. Not Moving!\n   SRC:{self.destnote0}\n   DST:{newnote}")
            return

        if not dry_run:
            shutil.move(self.destnote0, newnote)

        return newnote

    def grep(
        self,
        *expr,
        matchcase=False,
        full_note=False,
        full_word=False,
        fixed_strings=False,
        match_any=True,
    ):
        """
        Search the content of notes for expr

        Inputs:
        -------
        *expr ['']
            Expression to search. Can be regex. Also can pass a tuple or list. All
            arguments are flattened (list of strings) and combined

        matchcase [False]
            Whether or not to consider case in the expression

        full_note [False]
            Whether to search the entire note text or just the "notes" section

        fixed_strings [False]
            Match the string exactly. i.e. does a re.escape() on the pattern

        full_word [False]
            If True, matches the full word. Basically add \\b to each pattern

        match_any [True]
            Whether to match any expr

        Returns: Bool
        """
        import re

        flags = re.MULTILINE | re.UNICODE
        if not matchcase:
            flags |= re.IGNORECASE

        expr = list(flattenlist(expr))  # will make  a list of all strings

        if fixed_strings:
            expr = [re.escape(e) for e in expr]

        if full_word:
            expr = [r"\b" + e + r"\b" for e in expr]

        # For all, you need individual regexes but for any, can make a single one
        if match_any:
            requery = re.compile("|".join(expr), flags=flags)
            query = lambda qtext: bool(requery.search(qtext))
        else:
            requeries = [re.compile(e, flags=flags) for e in expr]
            query = lambda qtext: all(r.search(qtext) for r in requeries)

        if not self._data:
            # To speed this up grep the raw text first before even trying to parse the
            # note. This is a double search but is almost certainly faster than always
            # parsing and only done if we didn't read already
            txt = getattr(self, "txt", None)
            if txt and not query(txt):
                return False
            self.read()

        txt = self.txt

        if full_note:
            return query(txt)

        qtext = self.data.get(self.note_field, "")
        if not isinstance(qtext, str):
            debug("Note is {}. Converting to string".format(str(type(qtext))))
            qtext = str(qtext)  # Make it a string

        return query(qtext)

    def query(self, *expr, allow_exception=False, match_any=True, **kwargs):
        """
        Perform python queries on notes:

        Inputs:
        -------
        expr ['']
            Query expression(s). See query_help() for details. Also can pass a tuple
            or list. All arguments are flattened (list of strings) and combined

        allow_exception [False]
            If True, raises a warning instead of an exception

        match_any [True]
            Whether to match any expr. Also passed to grep

        **kwargs
            Passed to grep. Notably:
                matchcase,full_note,full_word,fixed_strings

        Returns:
            boolean of whether or not it matched
        """
        from functools import partial
        import re

        expr = list(flattenlist(expr))  # will make  a list of all strings

        ns = {
            "re": re,
            "ss": shlex.split,
            "note": self,
            "data": self.data,
            "tags": normalize_tags(self.data.get("tags", []), sort=False),
            "notes": self.data.get(self.note_field, ""),
            "text": getattr(self, "txt", ""),
        }

        ns["grep"] = functools.partial(self.grep, match_any=match_any, **kwargs)
        ns["g"] = ns["grep"]
        ns["gall"] = functools.partial(self.grep, match_any=False, **kwargs)
        ns["gany"] = functools.partial(self.grep, match_any=True, **kwargs)

        # Note that these get normalized which includes flattening them
        ns["tany"] = lambda *tags: any(t.lower() in ns["tags"] for t in normalize_tags(tags))
        ns["tall"] = lambda *tags: all(t.lower() in ns["tags"] for t in normalize_tags(tags))
        ns["t"] = ns["tany"]

        for expri in expr:
            full_expr = [i.strip() for i in expri.replace("\n", ";").split(";") if i.strip()]
            full_expr[-1] = "_res = " + full_expr[-1]

            for ii, line in enumerate(full_expr):
                try:
                    exec(line, ns)
                except Exception as E:
                    err = E.__class__.__name__
                    desc = str(E)
                    etxt = 'Line {} `{}` raised {}. MSG: "{}". Note: "{}"'.format(
                        ii, line, err, desc, self.names0.filename
                    )
                    if allow_exception:
                        warn("Query Error: {}".format(etxt))
                        ns["_res"] = False
                    else:
                        raise QueryError(etxt)

            r = bool(ns["_res"])

            # Short circuit
            if not match_any:
                if not r:
                    return False
            else:
                if r:
                    return True

        # At this point, we either hit them all with ALL, we hit none with ANY
        return not match_any

    def _isbroken_broken_from_hide(self):
        """
        Returns whether a link note is broken from being hidden
        """
        if self.link != "both" or not self.islink:
            return False

        # Is it a link and is it NOT broken (is a file)
        if os.path.islink(self.destnote0) and os.path.isfile(self.destnote0):
            return False

        # Finally make sure the *correct* dest exists:
        if not os.path.isfile(self.destnote):
            return False  # Still broken but not repairable

        return True

    def _read_from_broken_link_from_hide(self):
        """
        Tries to read from a broken link due to hidden but does NOT repair!
        (reading shouldn't modify content)
        """
        for destnote in get_filenames(self.destnote)[1:]:
            if exists_or_link(destnote):
                break
        else:
            raise FileNotFoundError(f"Cannot find {repr(self.destnote)}")
        for linkdest in get_filenames(os.readlink(destnote))[1:]:
            if exists_or_link(linkdest):
                break
        else:
            raise FileNotFoundError(f"Cannot find link for {repr(self.destnote)}")

        with open(linkdest) as fobj:
            return fobj.read()

    def __str__(self):
        return f"Notefile({repr(self.names0.filename)})"

    __repr__ = __str__


class QueryError(ValueError):
    pass


class MultipleNotesError(ValueError):
    pass


def get_filenames(filename):
    """
    Normalize filenames for NOTESEXT

    If given a hidden notefile, assumes the base name is
    NOT hidden.

    returns:
        notenames NamedTuple
    """
    (base, name) = os.path.split(filename)

    if name.endswith(NOTESEXT):  # Given a notefile path
        if name.startswith("."):  # Given a HIDDEN file
            vis_note = name[1:]
            hid_note = name
            name = name[1 : -len(NOTESEXT)]  # Assume *NOT* hidden
        else:
            vis_note = name
            hid_note = "." + name
            name = name[: -len(NOTESEXT)]
    else:
        if name.startswith("."):  # file itself is hidden
            vis_note = hid_note = name + NOTESEXT
        else:
            vis_note = name + NOTESEXT
            hid_note = "." + vis_note

    filename = os.path.normpath(os.path.join(base, name))
    vis_note = os.path.normpath(os.path.join(base, vis_note))
    hid_note = os.path.normpath(os.path.join(base, hid_note))
    return Bunch(
        filename=filename,
        visible=vis_note,
        hidden=hid_note,
        vsubdir=f"_notefiles/{vis_note}",
        hsubdir=f".notefiles/{vis_note}",
    )


def hidden_chooser(names, *, hidden, subdir):
    """
    Simple util but I keep needing it.

    Searches for an existing notefile searching in order of `hidden`.

    Retuns:
        notefilepath,<whether or not it exists>,is_hidden,is_subdir

    where the latter two are based on the settings if not found
    """
    # Set the order to test based on hidden and subdir
    # but note that hidden is considered priority over subdir
    if hidden and subdir:
        testfiles = [names.hsubdir, names.hidden, names.vsubdir, names.visible]
    elif not hidden and subdir:
        testfiles = [names.vsubdir, names.visible, names.hsubdir, names.hidden]
    elif hidden and not subdir:
        testfiles = [names.hidden, names.hsubdir, names.visible, names.vsubdir]
    elif not hidden and not subdir:
        testfiles = [names.visible, names.vsubdir, names.hidden, names.hsubdir]

    lookup = {  # is_hidden,is_subdir
        names.hsubdir: (True, True),
        names.hidden: (True, False),
        names.vsubdir: (False, True),
        names.visible: (False, False),
    }

    found = []

    for testfile in testfiles:
        if exists_or_link(testfile):
            is_hidden, is_subdir = lookup[testfile]
            found.append((testfile, True, is_hidden, is_subdir))

    if len(found) > 1:
        txt = f"Too many notes exist for {names.filename!r}: "
        txt += ", ".join(f"{n[0]!r}" for n in found)
        raise MultipleNotesError(txt)

    if found:
        return found[0]

    return testfiles[0], False, hidden, subdir  # Return the first one and does not exists


def exists_or_link(filename):
    """
    exists will return false if a broken link. This will NOT
    """
    return os.path.isfile(filename) or os.path.islink(filename)
