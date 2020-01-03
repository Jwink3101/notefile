"""
Symlink all tags

Assumes python 3.6+
"""
import sys
import os
import shutil

import ruamel.yaml
yaml = ruamel.yaml.YAML()

sys.path.append(os.path.abspath('..'))
import notefile
print(notefile.__version__) # 20200103

SOURCE = '/full/path/to/source'
DEST = '/full/path/to/links/'

def mkdir(s):
    try:
        os.makedirs(s)
    except OSError: 
        pass

#############################
### BE CAREFUL -- But this *should* be uncommented otherwise there will be lots
#                 of increments

# try:
#     shutil.rmtree(DEST)
# except OSError:
#     pass
###########################

mkdir(DEST)

cmd = ['list-tags','--path',SOURCE,'--out-file','tmp.yaml']
cmd.append('--exclude-links') # Optional

notefile.cli(cmd)

with open('tmp.yaml') as F:
    tags = yaml.load(F)
    tags = dict(tags)

for tag,files in tags.items():
    tagdest = os.path.join(DEST,tag)
    mkdir(os.path.join(DEST,tag))
    for file in files:
        dst = os.path.join(tagdest,os.path.split(file)[-1])
        
        # Handle duplicate filenames
        inc = None
        while os.path.exists(dst):
            if inc is None:
                main,ext = os.path.splitext(dst)
                dst = main + '.1' + ext
                inc = 1
            else:
                inc += 1
                main,ext = os.path.splitext(dst)
                main,_ = os.path.splitext(main)
                dst = main + f'.{inc}' + ext

        
        src = os.path.relpath(file,tagdest)
        os.symlink(src,dst)
    
