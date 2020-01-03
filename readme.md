# Notefile

(Beta Software)

notefile is a tool to quickly and easily manage metadata files ("notefiles") along with the file itself.

It is not a perfect solution but it does address many main concerns and issues.

Notefile is designed to assist in keeping associated notes and to perform the most basic opperations. However, it is not designed to do all possible things. Notes can be modified (in YAML) as needed with other tools including those included here.

It is also worth noting that while notefile can be used interactively, it is really design to be primarily a CLI

## Design & Goals

When a note or tag is added, an associated file is created in the same location. The design is a compromise of competing factors. For example, extended attributes are great but they are easily broken. Other metadata like ID3 or EXIF changes the file itself and is domain-specific. 

Similarly, single-database solutions are cleaner but risk damage and data-issues. Plus, it is easier to forgot that they are running in at the same time.

The format is YAML and should not be changed. However, this code does not assume any given fields except:

* filename
* filesize
* sha256
* tags
* notes

Any other data can be added and will be preserved.

## Repairable Issues:

* Mismatched Hash:
    * This means it is still `filename.ext` and `filename.ext.note.txt` but the hash is wrong. 
        * Check size first. If size is wrong, then hash has to be wrong. Otherwise, hash it
* Missing filename:
    * `filename.ext.note.txt` exists but `filename.ext` is missing. 
    * Look for any file that is the same size then same hash --> repair
    * If it can't repair, look for same name


## Tips

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

