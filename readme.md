# Notefile

notefile is a tool to quickly and easily manage sidecar metadata files ("notefiles") along with the file itself as a YAML file (with the extensions `.notes.yaml`).

It is not a perfect solution but it does address many main needs as well as concerns I have with alternative tools.

Notefile is designed to assist in keeping associated notes and to perform the most basic operations. However, it is not designed to do all possible things. Notes can be modified (in YAML) as needed with other tools including those included here.

It is also worth noting that while notefile can be used as a Python module, it is really design to be primarily a CLI.

## Design & Goals

When a note or tag is added, a notefile is created in the same location with the same name plus `.notes.yaml`. The design is a compromise of competing factors of the alternatives.

For example, extended attributes are great but they are easily broken and are not always compatible across different operating systems. Other metadata like ID3 or EXIF changes the file itself and are domain-specific. 

Similarly, single-database solutions (like [TMSU](https://tmsu.org/)) are cleaner but risk damage and are a single point of failure (corruption and recoverability). And it is not as explicit that they are being used on a file.

YAML notefiles provide a clear indication of their being a note (or tag) of interest and are cross-platform. Furthermore, by being YAML text-based files, they are not easily corrupted. Also, YAML files are easily read and written by humans.

The format is YAML and should not be changed. However, this code does not assume any given fields except:

* filesize
* sha256 (optional)
* tags
* notes

Any other data can be added and will be preserved across all actions.

## Install and Usage

### Install

Install right from github:

    $ python -m pip install git+https://github.com/Jwink3101/notefile.git

### Usage

Every command is documented. For example, run

    $ notefile -h

to see a list of commands and universal options and then

    $ notefile <command> -h

for specific options.

The most basic command will be

    $ notefile edit file.ext

which will launch `$EDITOR` (or try other global variables) to edit the notes. You can also use 

    $ notefile tag -t mytag file.ext

to add tags.


## Repairs

It is possible for the sidecar notefiles to get out of sync with the basefile. The two possible issues are:

* **metadata**: The basefile has been modified thereby changing its size, sha256, and mtime
* **orphaned**: The basefile has been renamed thereby orphaning the notefile

The `repair` function can repair either (but *not* both) types of issues. To repair metadata, the notefile is simply updated with the new file.

To repair an orphaned notefile, it will search in and below the current directory for the file. It will first compare file sizes and then compare sha256 values. If more than one possible file is the original, it will *not* repair it and instead provide a warning.

## File Hashes

By default, the SHA256 hash is computed. It is *highly* suggested that this be allowed since it greatly increases the integrity of the link between the basefile and the notefile sidecar. However, `--no-hash` can be passed to many of the functions and it will disable hashing.

Note that when using `--no-hash`, the file may still be rehashed in subsequent runs without  `--no-hash`, depending on the opperation.

When repairing an orphaned notefile, candidate files are first compared by filesize and then by SHA256. While not foolproof, this *greatly* reduces the number of SHA256 computations to be performed; especially on larger files where it becomes increasingly unlikely to be the exact same size.

## Hidden Notefiles

Notefiles can be either visible (default) or can be hidden with a preceeding dot. They are visible by default but can be made to default to hidden by setting the environmental variable `NOTEFILE_HIDDEN=true` (any other value will be false). Regardless of the default, each note can be created as hidden or visible with `-V, --visible` or `-H, --hidden` flags.

Note that the flags *only* apply to creating a *new* note. For example if a visible note already exists, it will always go to that even if `-H` is set.

To hide or unhide a note, use `notefile vis hide` or `notefile vis show` on either file(s) or dir(s). If specified as dir, will apply to all items following exclusion flags.

Changing the visibility of a symlinked referent will cause the symlinked note to be broken. However, by design it will still properly read the note and will be fixed when editing or repairing metadata.

Hidden notefiles are more easily orphaned since it is harder to move both files but not having a directory filling with notefiles can be helpful. 

## Tips

### Scripts

Includes are some [scripts](scripts/) that may prove useful. As noted before, the goal of `notefile` is to be capable but it doesn't have to do everything! 

In those scripts (and the tests), actions are often performed by calling the `cli()`. While less efficient, `notefile` is *really* designed with CLI in mind so some of the other functions are less robust.

### Tracking History

`notefile` does not track the history of notes and instead suggest doing so in git. They can either be tracked with an existing git repo or its own.

If using it on its own, you can tell git to only track notes files with the following in your  `.gitignore`:

```git
# Ignore Everything except directories, so we can recurse into them
*
!*/

# Allow these
!*.notes.yaml
!.gitignore
```

Alternatively, the `export` command can be used.

## Known Issues

These will likely be addressed (roughly in order of priority)

* Behavior with hidden files themselves is not consistent. A warning will be thrown

## Additional Workflows

This tools includes a lot of features but does not include everything. More can be done in Python direction. 

For example, to rename a tag from `old` to `new`:

```python
import notefile
for note in notefile.find_notes(return_note=True):
    note.read() # Access to data attribute
    if 'old' in note.data.get('tags',[]): # tags may not always exist
        note.modify_tags(add='new',remove='old')
        note.write()
        print(note.filename)
```

Additional fields can be added (or removed) from `data` and will be saved when `write` is called.

## Changelog

See [Changelog](changelog.md)
