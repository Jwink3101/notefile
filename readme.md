# Notefile

(Beta Software)

notefile is a tool to quickly and easily manage metadata files ("notefiles") along with the file itself as associated YAML files.

It is not a perfect solution but it does address many main concerns and issues.

Notefile is designed to assist in keeping associated notes and to perform the most basic opperations. However, it is not designed to do all possible things. Notes can be modified (in YAML) as needed with other tools including those included here.

It is also worth noting that while notefile can be used as a Python module, it is really design to be primarily a CLI.

## Design & Goals

When a note or tag is added, an associated file is created in the same location. The design is a compromise of competing factors. For example, extended attributes are great but they are easily broken and are not always compatible across different operating systems. Other metadata like ID3 or EXIF changes the file itself and is domain-specific. 

Similarly, single-database solutions are cleaner but risk damage and are a single point of failure (corruption and recoverability). And it is not as explicit that they are being used at the same time.

Associated YAML notefiles provide a clear indication of their being a note (or tag) of interest and are cross-platform. Furthermore, by being YAML text-based files, they are not easily corrupted.

The format is YAML and should not be changed. However, this code does not assume any given fields except:

* filename
* filesize
* sha256
* tags
* notes

Any other data can be added and will be preserved.

## Install and Usage

### Install

Install right from github:

    $ pip install git+https://github.com/Jwink3101/notefile.git

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


## Repairable Issues:

* Mismatched Hash:
    * This means it is still `filename.ext` and `filename.ext.note.txt` but the hash is wrong. 
        * Check size first. If size is wrong, then hash has to be wrong. Otherwise, hash it
* Missing filename:
    * `filename.ext.note.txt` exists but `filename.ext` is missing. 
    * Look for any file that is the same size then same hash --> repair
    * If it can't repair, look for same name


## Tips

### Scripts

Includes are some [scripts](scripts/readme.md) that may prove useful. As noted before, the goal of `notefile` is to be capable but it doesn't have to do everything! 

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



