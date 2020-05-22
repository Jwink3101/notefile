#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tool to make symlinks out of notefile grep results.

Arguments: dest ['.'] Where to make the symlinks

Example:
    $ notefile grep <query> | /path/to/pipe_grep_results_symlinks.py dest
    
Note:
    This is very rough and barebones. Very little help or input validation.
"""
import sys,os

if '-h' in sys.argv or '--help' in sys.argv:
    print(__doc__)
    sys.exit()

dest = '.'
if len(sys.argv) > 1:
    dest = sys.argv[1]

try:
    os.makedirs(dest)
except OSError:
    pass

for line in sys.stdin:
    line = line.strip()
    src = os.path.relpath(line,dest)
    src0 = os.path.normpath(src)
    dst = os.path.join(dest,os.path.basename(line))
    
    c = 0
    for i in range(50):
        try:
            src = os.path.normpath(src)
            dst = os.path.normpath(dst)
            os.symlink(src,dst)
            print(f"link '{src}' --> '{dst}'")
            break
        except OSError:
            # File exists
            c += 1
            a,b = os.path.splitext(dst)
            if c > 1:
                # Remove the prev .N tag
                a,_ = os.path.splitext(a)
                
            dst = a + f'.{c}' + b
    else:
        print(f'ERROR: Too many similar files to {src0}')
        sys.stdout.flush() # so it prints right away
                
        
    

