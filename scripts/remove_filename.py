"""
Removes filenames from specified directories. As of 20200521.0, the filename
is no longer tracked. However, this tool is designed to keep all fields 
so it won't otherwise remove it
"""

# This isn't needed it notefile is installed but (a) makes sure the latest
# version is being used and (b) is useful in testing
import sys,os
sys.path.insert(0,os.path.abspath('..'))

import notefile
print(notefile.__version__) # 20200517.0

# You need to set the DEST and any of these optiojs
DEST = "/path/to/notes"

for note in notefile.find_notes(path=DEST,
                                excludes=None,matchcase=False,
                                maxdepth=None,
                                exclude_links=False,
                                include_orphaned=False,
                                noteopts=None,
                                # DONT change this:
                                return_note=True):
    note.read()
    if 'filename' in note.data:
        del note.data['filename']
        note.write()
        print(note.filename)
