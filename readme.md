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

## JSON vs YAML

Notefile can write the notes as nicely-formatted YAML or as JSON (which is technically still YAML as YAML is a superset of JSON). JSON is that it is *much* faster to read than YAML but comes at cost of being hard to edit manually.

The extension will **always** be `.yaml` as YAML is a superset of JSON and any YAML parser should be able to read JSON

## Install and Usage

### Install

Install right from github:

    $ python -m pip install git+https://github.com/Jwink3101/notefile.git

Optional PyYAML backend (LibYAML speedup when available):

    $ python -m pip install "git+https://github.com/Jwink3101/notefile.git#egg=notefile[pyyaml]"

### Requirements

The only *real* requirement is `ruamel.yaml`. However, if you have `pyyaml` ([website](https://pyyaml.org/)) installed, notefile will use that as a faster **read-only** parser (writes still use ruamel.yaml). Even better, if you have [LibYAML](https://pyyaml.org/wiki/LibYAML), it will be about 25x faster for reads.

Note: We avoid writing with PyYAML due to known issues. See [PyYAML issue #121](https://github.com/yaml/pyyaml/issues/121).

To install LibYAML, see: (based on [these instructions](https://pyyaml.org/wiki/LibYAML)):

> Download the source package: http://pyyaml.org/download/libyaml/yaml-0.2.5.tar.gz.
> 
> To build and install LibYAML, run
> 
>     $ ./configure
>     $ make
>     # make install

Then to install pyyaml,

    $ python -m pip install pyyaml

Or via the optional extra:

    $ python -m pip install "notefile[pyyaml]"

In my (limited) experience, pyyaml comes with Anaconda but not miniconda

### Usage

Every command is documented. For example, run

    $ notefile -h

to see a list of commands and universal options and then

    $ notefile <command> -h

for specific options.

The most basic command will be

    $ notefile edit file.ext

which will launch `$EDITOR` (or try other global variables) to edit the notes. You can also use 

    $ notefile mod -t mytag file.ext

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

## Hidden and Subdir Notefiles

Notes can be hidden and/or in a subdirectory. Consider `file.txt`. When a note is *created* with the following flags, the location of the note is as follows:

| Flags                   | Note Destination                 | comment |
|-------------------------|----------------------------------|---------|
| `--visible --no-subdir` | `file.txt.notes.yaml`            | default |
| `--visible --subdir`    | `_notefiles/file.txt.notes.yaml` |         |
| `--hidden --no-subdir`  | `.file.txt.notes.yaml`           |         |
| `--hidden --subdir`     | `.notefiles/file.txt.notes.yaml` |         |


The default is `--visible` and `--no-subdir` but both can be controlled with environmental variables:

    $ export NOTEFILE_HIDDEN=true
    $ export NOTEFILE_SUBDIR=true


Note that the flags *only* apply to creating a *new* note. For example if a visible note already exists, it will always go to that even if `-H` is set.

To hide or unhide a note, use `notefile vis hide` or `notefile vis show` on either file(s) or dir(s). These will also use the subdir setting

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

- Behavior with hidden files themselves is not consistent. A warning will be thrown

## Additional Workflows

This tools includes a lot of features but does not include everything. More can be done in Python directly

For example, to search for all notes and perform a test do 

```python
import notefile
for note in notefile.find(return_note=True):
    # test on note.data (which is read automatically)
```

Additional fields can be added (or removed) from `data` and will be saved when `write` is called.

Note that notefile does support setting alternative note fields (but not tags) so that may be useful from the CLI.

## Changelog

See [Changelog](changelog.md)
