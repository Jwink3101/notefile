#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Write notesfiles to accompany main files
"""
from __future__ import division, print_function, unicode_literals
__version__ = '20200106.0'
__author__ = 'Justin Winokur'

import sys
import os
import subprocess
import hashlib
import tempfile
import shutil
import datetime
import time
import argparse
import fnmatch
import re
from collections import defaultdict,OrderedDict

if sys.version_info[0] > 2:
    unicode = str

NOTESTXT = '.notes.yaml'
NOHASH = '** not computed **'

DEBUG = False
def debug(*args,**kwargs):
    if DEBUG:
        s = ', '.join('{}'.format(a) for a in args)
        print('DEBUG: {}'.format(s),**kwargs)

#### Set up YAML
try:
    import ruamel.yaml
    from ruamel.yaml.scalarstring import PreservedScalarString as PSS
    yaml = ruamel.yaml.YAML()
except ImportError:
    pass # This is only done when setting up

def pss(item):
    """
    Convert strings with '\n' to PreservedScalarString
    and recurse into dicts and lists
    """
    if isinstance(item,list): # Is actually a list
        return [pss(i) for i in item]
    elif isinstance(item,dict):
        item = item.copy()
        for key,val in item.items():
            item[key] = pss(val)
        return item
    elif isinstance(item,(str,unicode)) and '\n' in item:
        return PSS(item)
    else:
        return item

#### /Set up YAML

#### Utils

def touni(s):
    if isinstance(s,(tuple,list)):
        return type(s)([touni(i) for i in s])
    try:
        return s.decode('utf8')
    except:
        pass
    return s

def now_string(pm=False):
    """
    print the current time with time zone
    
    if `pm=False` will print the time zone with '+' or '-'. Otherwise, will use
        '+' --> 'p'
        '-' --> 'n'
    
    From http://stackoverflow.com/a/1111655
    """
    # we want something like '2007-10-18 14:00+0100'
    tz = -time.timezone
    mytz = '%+03d' % (tz//3600)+ ':00' #TODO: 1/2 hour time zones
    if pm:
        mytz = mytz.replace('+','p').replace('-','n')
    dt  = datetime.datetime.now()
    dts = dt.strftime('%Y-%m-%d %H:%M:%S')  # %Z (timezone) would be empty
    nowstring="%s %s" % (dts,mytz)
    return nowstring

def get_filenames(filename):
    """
    Normalize filenames for NOTESTXT
    """
    filename = touni(filename)
    if filename.endswith(NOTESTXT):
        return filename[:-len(NOTESTXT)],filename
    return filename,filename + NOTESTXT

def sha256(filepath,blocksize=2**20):
    """
    Return the sha256 hash of a file. 
    
    `blocksize` adjusts how much of the file is read into memory at a time.
    This is useful for large files.
        2**20: 1 mb
        2**12: 4 kb
    """
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()

def read_data(filename,link='both'):
    """
    Read the data for a given filename and return 
    filename,data (where filename has been cleaned with `get_filenames`.
    
    link ['both']
        Where to read the data. For 'both' or 'symlink', will read the linked
        note setting. For 'source', will find the source file and read that note
    
    """
    if not link in {'both','symlink','source'}:
        raise ValueError("'link' must be in {'both','symlink','source'}")
    filename,notesfile = get_filenames(filename)
    
    if os.path.islink(filename) and link == 'source':
        destfile = os.readlink(filename)
        _,notesfile = get_filenames(destfile)
    
    if not os.path.exists(notesfile):
        debug('{} does not exist. New dict'.format(notesfile))
        stat = os.stat(filename)
        data = {'filename': os.path.basename(filename),
                'filesize': stat.st_size,
                'sha256':NOHASH,
                'mtime':stat.st_mtime}
    else:
        debug('Loading {}'.format(notesfile))
        with open(notesfile,'rt') as file:
            data  = yaml.load(file)
    if 'tags' not in data:
        data['tags'] = []
            
    if 'notes' not in data:
        data['notes'] = ''
    return filename,data

def write_data(filename,data,link='both',hashfile=True):
    """
    Write/update the data for a given filename. 
    
    link [both]
        Where to write the notes.
            'both': Write to the referent (source) and symlink the notes file 
                    too
            'symlink': Write only to the link-file
            'source': Write only to the referent (source) file
        
        Note: Links are *not* recursively followed!
    """
    if not link in {'both','symlink','source'}:
        raise ValueError("'link' must be in {'both','symlink','source'}")
    filename,notesfile = get_filenames(filename)

    data = pss(data) # Will recurse into lists and dicts too
    
    if hashfile and data['sha256'] == NOHASH:
        data['sha256'] = sha256(filename)
    
    data['last-updated'] = now_string()
    data['notefile version'] = __version__
    try:
        data = ruamel.yaml.comments.CommentedMap(data)
        data.yaml_set_start_comment('YAML Formatted notes created with notefile version {}'.format(__version__))
    except TypeError:
        pass # Likely due to python2 and ordering
 
    # Write to tmp and swap. Makes write atomic
    with tempfile.NamedTemporaryFile(delete=False,mode='wt') as file:
        yaml.dump(data,file)

    if not os.path.islink(filename) or link == 'symlink':    
        shutil.move(file.name,notesfile)
    else:
        # Write to the source file
        destfile = os.readlink(filename)
        _,destnotesfile = get_filenames(destfile)
        shutil.move(file.name,destnotesfile)
        if link == 'both':
            try:
                os.remove(notesfile)
            except:
                pass
            os.symlink(destnotesfile,notesfile)
                
    debug('Wrote',notesfile)

###########
def interactive_edit(filename,link='both',hashfile=True):
    filename,data = read_data(filename,link=link)
    editor_names = ['EDITOR','GIT_EDITOR','SVN_EDITOR','LOCAL_EDITOR']
    for editor_name in editor_names:
        try:
            editor = os.environ[editor_name]
            break
        except KeyError:
            pass
    else:
        raise ValueError(('Must specify an editor. Possible enviormental variables: '
                         (', '.join("'{}'".format(e) for e in editor_names))))

    header= "# Add or edit any notes below. This line will be removed\n\n"
    with tempfile.NamedTemporaryFile(delete=False,mode='wt') as file:
        file.write(header + data.get('notes',''))

    subprocess.check_call([editor,file.name])

    with open(file.name,'rt') as f:
        newtxt = f.read()

    newtxt = newtxt.strip().splitlines()
    
    if len(newtxt) >0 and newtxt[0].startswith(header[:10]):
        newtxt.pop(0)
        
    newtxt = '\n'.join(newtxt)
    data['notes'] = newtxt.strip()
    write_data(filename,data,link=link,hashfile=hashfile)

def add_note(filename,note,replace=False,link='both',hashfile=True):
    """
    Add notes to the file. 
    
    Options:
    --------
    replace [False]
        If True, will overwrite the current notes. Tags remain!
    
    link:
        How to handle the links. See write_data
    
    Does not repair. Call repair seperately
    """
    filename,data = read_data(filename,link=link)
    if replace or len(data['notes'].strip()) == 0:
        data['notes'] = note.strip()
    else:
        data['notes'] += '\n\n' + note.strip()
            
    write_data(filename,data,link=link,hashfile=hashfile)   
    
def modify_tags(filename,tags,remove=False,link='both',hashfile=True):
    """Add (or remove) tag(s) for a file
    
    Options:
    --------
    remove [False]
        If True, will remove the specifed tag(s)
    link:
        How to handle the links. See write_data
    
    """
    filename,data = read_data(filename,link=link)
    data0 = data.copy()
    if 'tags' not in data:
        data['tags'] = []
    data['tags'] = [tag.lower() for tag in data['tags']] # make a mutable list
    
    if isinstance(tags,(str,unicode)):
        tags = [tags] # make a list
    
    for tag in tags:
        tag = tag.lower()
        if remove: 
            try:
                data['tags'].remove(tag)
            except ValueError:
                pass
            continue
        
        if tag not in data['tags']:
            data['tags'].append(tag)
    if data != data0:
        write_data(filename,data,link=link,hashfile=hashfile)

def cat(filename,tags=False,stream=sys.stdout,full=False):
    """
    cat the notes or tags for a given file
    """
    
    if full:
        _,notefile = get_filenames(filename)
        with open(notefile,'rt') as F:
            print(F.read(),file=stream)
        return
    
    _,data = read_data(filename)
    
    if tags:
        for tag in sorted(data['tags'],key=lambda s:s.lower()):
            print(tag,file=stream)
    else:
        print(data['notes'],file=stream)
    

##### Repairs            
def find_by_size_hash(path,size,sha,excludes=None,matchcase=False):
    """
    Find potential basefiles based on thier size and hash. Check sizes first and
    then only hash if the size matches
    """
    possible = []
    for root, dirs, files in os.walk(path):
        exclude_in_place(files,excludes,matchcase=matchcase,isdir=False)
        exclude_in_place(dirs,excludes,matchcase=matchcase,isdir=True)

        files.sort(key=lambda s:s.lower())
        for file in files:
            file = os.path.join(root,file)
            if not os.stat(file).st_size == size:
                continue
            if sha256(file) == sha:
                possible.append(file)
    return possible

def find_notes(path,excludes=None,matchcase=False,
               exclude_links=False,
               _return_orphaned=False,_return_both=False):
    """
    find notes recurisvly starting in `path`
    
    Options:
    --------
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    """
    notes = set()
    orphaned = set()
    for root, dirs, files in os.walk(path):        
        exclude_in_place(files,excludes,matchcase=matchcase,isdir=False)
        exclude_in_place(dirs,excludes,matchcase=matchcase,isdir=True)

        notefiles = set(file for file in files if file.endswith(NOTESTXT))

        for file in files:
            file,notefile = get_filenames(file)

            if exclude_links and os.path.islink(os.path.join(root,notefile)):
                continue
                
            if not notefile in notefiles:
                continue # Not a note or doesn't have a note
            
            if file not in files:
                orphaned.add(os.path.join(root,notefile))
            else:
                notes.add(os.path.join(root,notefile))
    if _return_both:
        return sorted(orphaned.union(notes))
    if _return_orphaned:
        return sorted(orphaned)
    return sorted(notes)


def exclude_in_place(mylist,excludes,isdir=False,matchcase=False):
    """
    Helper tool to apply exclusions IN PLACE in mylist
    """
    if excludes is None:
        excludes = []
    if isinstance(excludes,(str,unicode)):
        excludes = [excludes]
    
    if matchcase:
        case = lambda s:s
    else:
        case = lambda s:s.lower()
        excludes = [e.lower() for e in excludes]

    for item in mylist[:]: # Iterate a copy!
        if any(fnmatch.fnmatch(case(item),e) for e in excludes):
            mylist.remove(item)
            continue
        if isdir and any(fnmatch.fnmatch(case(item + '/'),e) for e in excludes):
            mylist.remove(item)
            continue

def repair_metadata(filename,force=False,dry_run=False,link='both',hashfile=True):
    """
    Update sha256 and size of filename
    """
    filename,data = read_data(filename,link=link)
    
    stat = os.stat(filename)
    size = stat.st_size
    mtime = stat.st_mtime
    
    if force or size != data.get('filesize',-1) or mtime != data.get('mtime',-1):
        if dry_run:
            return True
        debug('Updated {}'.format(filename))
        data['filesize'] = size
        if hashfile:
            data['sha256'] = sha256(filename)
        else:
            data['sha256'] = NOHASH
        data['mtime'] = mtime
        write_data(filename,data,link=link,hashfile=hashfile)
        
        return True
    return False

def repair(path,repair_type='both',dry_run=False,force=False,link='both',
           excludes=None,matchcase=False,hashfile=True,search_path='.'):
    """
    Repair notes:
    
    Inputs:
    -------
    path
        Specify path to repair. Specify a directory to repair all notes
        in that directory
    
    repair_type ['both'] -- optional
        Specify the type of repairs to make. Metadata repairs only fix the 
        metadata for the base file (and only check the hash if other metadata 
        is wrong or `force`). orphaned repairs look (in the current 
        directory and below) for a orphaned base file.
    
    dry_run [False] -- optional
        If True, do not do anything
    
    force [False]
        If True, will update all metadata on all notes. Requires rehashing the
        basefile. Otherwise, will only rehash if the mtime and size are 
        different
    
    link ['both']
        Specify how to handle symlinks
        
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    hashfile [True]
        Whether or not to ever compute the hash. Cannot repair orhaned if False
    
    search_path ['.']
        Where to search for missiung files
    """
    if os.path.isdir(path):
        filenames = find_notes(path,_return_both=True,
                               excludes=excludes,matchcase=matchcase)
    else:
        filenames = [path]
    
    if repair_type not in ['both','metadata','orphaned']:
        raise ValueError('Unrecognized repair_type')
    
    orphaneds = []
    for filename in filenames:
        basename,filename = get_filenames(filename)
        if not os.path.exists(basename):
            orphaneds.append(filename)
            continue
        
        if repair_type == 'orphaned':
            continue
            
        if repair_metadata(filename,force=force,dry_run=dry_run,hashfile=hashfile):
            print('{}Updated metadata for {}'.format('(DRY RUN) ' if dry_run else '',filename))
    
    if repair_type == 'metadata':
        return # Do not fix orphaned
    
    for orphaned in orphaneds:
        _,data = read_data(orphaned,link=link)
        if not hashfile or data['sha256'] == NOHASH:
            print('Cannot repair {} without hashes'.format(orphaned) )
            continue
            
        print("\norphaned basefile for '{}'".format(orphaned))
        
        candidates = find_by_size_hash(search_path,data['filesize'],data['sha256'],
                                       excludes=excludes,matchcase=matchcase)
        if len(candidates) == 0:
            print('No candidates found. Try running from a higher directory')
            continue
        if len(candidates) > 1:
            print('Multiple candiates found. Not doing anything')
            for candidate in candidates:
                print('    {}'.format(candidate))
            continue
            
        candidate = candidates[0]
        print('Found match: {}'.format(candidate))
        
        _,notesdest = get_filenames(candidate)
        if os.path.exists(notesdest):
            print('WARNING: Note already exists. Not repairing')
            continue
        print('{}Moving metadata {} --> {}'.format('(DRY RUN) ' if dry_run else '',orphaned,notesdest))
        if not dry_run:
            shutil.move(orphaned,notesdest)
##### /repairs

def grep(path,expr,expr_matchcase=False,
           excludes=None,matchcase=False,
           exclude_links=False,
           stream=sys.stdout):
    """
    Search notes for expr
    """
    flags = re.MULTILINE | re.UNICODE
    if not expr_matchcase:
        flags = flags | re.IGNORECASE
    requery = re.compile(expr,flags=flags)
    notes = find_notes(path,excludes=excludes,matchcase=matchcase,exclude_links=exclude_links)
    for note in notes:
        filename,data = read_data(note)
        if len(requery.findall(data['notes'])):
            print(filename,file=stream)


def list_tags(path,tags,
              excludes=None,matchcase=False,
              exclude_links=False,
              stream=sys.stdout):
   
    tags = [t.lower() for t in tags]
    
    notes = find_notes(path,excludes=excludes,matchcase=matchcase,exclude_links=exclude_links)
    
    tagout = defaultdict(list)
    
    # Decide if this needs to be a query based on whether or not any tag has a space
    if any(' ' in tag.strip() for tag in tags):
        # Queries
        query = ' or '.join(tags)
        for note in notes:
            filename,data = read_data(note)
            dd = defaultdict(lambda: False,{tag.lower():True for tag in data['tags']})
            if eval(query,dd):
                tagout[query].append(filename)
    else:
        tags = set(tags)                
        for note in notes:
            filename,data = read_data(note)
            for tag in data['tags']:
                if tag.lower() in tags or len(tags) == 0:
                    tagout[tag.lower()].append(filename)

    yaml.dump(dict(tagout),stream)

def export(path,
           excludes=None,
           matchcase=False,
           exclude_links=False,
           stream=sys.stdout):
       
    notes = find_notes(path,excludes=excludes,matchcase=matchcase,exclude_links=exclude_links)
    
    res = {}
    res['description'] = 'notefile export'
    res['time'] = now_string()
    res['notefile version'] = __version__
    res['notes'] = {}
    
    for note in notes:
        filename,data = read_data(note)
        res['notes'][filename] = pss(data)
    
    try:
        res = ruamel.yaml.comments.CommentedMap(res)
        res.yaml_set_start_comment('YAML Formatted notefile export')
    except TypeError:
        pass # Likely due to python2 and ordering
        
    yaml.dump(res,stream)
#     
def cli(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    
    if len(argv)==0 or argv[0] == 'help':
        argv = ['-h']
        
    description = """\
notefile -- Tool for managing notes, tags, etc in 
            associated *{} files""".format(NOTESTXT)
    epilog ="""\
Notes:
    * metadata is refreshed if mtime or size have changed.
      Or if `--force-refresh` and never if `--no-refresh`

    * If there exists *different* notefiles for a symlink and its source, 
      the notefile may be overwritten if `--link` is not set properly. 
      Use caution!
      
    * Tags should not be Python built-ins (e.g. "and", "or", "not") since
      the queries will not work. They should be valid Python variables names
      (i.e. should not contain spaces or characters like a "-")
    
"""
    
    parsers = {}
    parsers['main'] = argparse.ArgumentParser(\
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    subpar = parsers['main'].add_subparsers(
                dest='command',
                title='commands',
                help='execute `%(prog)s <command> -h` for help')
    
    parsers['main'].add_argument('--debug',action='store_true',help=argparse.SUPPRESS)
    parsers['main'].add_argument('-v','--version', action='version', version='%(prog)s-' + __version__)

    ## Modifiers

    parsers['add'] = subpar.add_parser('add',help='Add notes to a file')
    parsers['add'].add_argument('file',help='Specify file for additional notes')
    parsers['add'].add_argument('note',nargs='+',
        help=('Notes to add to a file. Use quotes as needed. '
              "Multiple arguments will be joined. Specify as a *single* '-' to "
              "read from stdin"))
    parsers['add'].add_argument('-r','--replace',action='store_true',
        help='Replace ratherthan append the new note')
        
    parsers['edit'] = subpar.add_parser('edit',
        help="Launch $EDITOR to interactivly edit the notes for a file") 
    parsers['edit'].add_argument('file',help='Specify file to edit')
    
    parsers['tag'] = subpar.add_parser('tag',
        help="Add or remove tags from file") 
    parsers['tag'].add_argument('-r','--remove',action='store_true',
        help='Remove tag on file(s) if present')
    parsers['tag'].add_argument('-t','--tag',action='append',required=True,
        help='Specify tag to add or remove. Must specify at least one. Tags are made lowercase.')
    parsers['tag'].add_argument('file',help='File(s) to tag',nargs='+')

    parsers['repair'] = subpar.add_parser('repair',
        help=("Verify basefile and metadata. Note that unless `--force-refresh`, "
              "files with matching mtime and size are *NOT* rehashed. "))
    parsers['repair'].add_argument('path',nargs='?',default='.',
        help=("['.'] Specify the path to repair. If PATH specific file, will only "
              'repair that file. If PATH is a directory, will recursivly repair all items. '
              'Will only grep in or below the *current* directory for orphaned files.'))
    parsers['repair'].add_argument('-d','--dry-run',action='store_true',
        help='Do not make any changes')
    parsers['repair'].add_argument('-t','--type',choices=['both','metadata','orphaned'],
        default='both',
        help=("['both'] Specify the type of repairs to make. Metadata repairs only fix the "
              "metadata for the base file (and only checks the hash if other metadata "
              "is wrong or if `--force-refresh`). Orphaned repairs look (in the "
              "current directory and below) for an orphaned basefile."))
    parsers['repair'].add_argument('--search-path',default='.',metavar='PATH',
        help=('[%(default)s] Specify the path to search for the basefile for '
              'orphaned notefiles. WARNING: Will recurse the _entire_ path '
              'which may be very slow for large directories'))
    
    ## Queries
    parsers['cat'] = subpar.add_parser('cat',help="Print the notes")
    parsers['cat'].add_argument('file',help='Specify file to cat')
    parsers['cat'].add_argument('-t','--tags',action='store_true',
        help='Print tags rather than notes') 
    parsers['cat'].add_argument('-f','--full',action='store_true',
        help='Prints the entire YAML notefile') 
    
    
    parsers['grep'] = subpar.add_parser('grep',help="Search notes for a given string")
    parsers['grep'].add_argument('expr',nargs='+',
        help='Search expression. Follows python regex patterns. Specify as "" to list all files with notes')
    parsers['grep'].add_argument('--match-expr-case',action='store_true',dest='match_expr_case',
        help='Match case on expr')
    parsers['grep'].add_argument('-p','--path',default='.',help='[%(default)s] Specify path')
    
    parsers['list_tags'] = subpar.add_parser('list-tags',help="List all files with the specific tag(s) or all tags. Prints in YAML format")
    parsers['list_tags'].add_argument('tags',nargs='*',
        help=('Specify tag(s) to list. If empty, lists them all. If multiple, it is an "or" search. '
              'Alternativly, specify a quoted query like "(tag1 or tag2) and not tag3"'))
    parsers['list_tags'].add_argument('-p','--path',default='.',help='[%(default)s] Specify path')

    parsers['export'] = subpar.add_parser('export',help="Export all notesfiles to YAML")
    parsers['export'].add_argument('-p','--path',default='.',help='[%(default)s] Specify path')

    
    ## Common arguments
    # Could use various parent parsers but this is honestly just as easy!
    
    # Modification Flags 
    for name in ['add','edit','tag','repair']:
        parsers[name].add_argument('--no-hash',action='store_false',dest='hashfile',
            help='Do *not* compute the SHA256 of the basefile. Will not be able to repair orphaned notes')
        parsers[name].add_argument('--no-refresh',action='store_true',
            help='Never refresh file metadata when a notefile is modified')
        parsers[name].add_argument('--force-refresh',action='store_true',
            help='Force %(prog)s to refresh the metadata of files when the notefile is modified')
        parsers[name].add_argument('--link',choices=['source','symlink','both'],
            default='both',
            help=("['%(default)s'] Specify how to handle symlinks. "
                  "If 'source', will add the notefile to the source only (non-recursively). "
                  "If 'symlink', will add the notefile to *just* the symlink file. "
                  "If 'both', will add the notefile the source (non-recursivly) and then symlimk to that notefile"))


    # Add exclude options:
    for name in ['repair','grep','list_tags','export']:
        parsers[name].add_argument('--exclude',action='append',default=[],
            help=('Specify a glob pattern to exclude when looking for notes. '
                  "Directories are also matched with a trailing '/'"))
        parsers[name].add_argument('--match-exclude-case',action='store_true',
            dest='match_case',help='Match case on exclude patterns')

    # add outfiles
    for name in ['list_tags','cat','grep','export']:
        parsers[name].add_argument('-o','--out-file',help='Specify file rather than stdout')

    # exclude links
    for name in ['list_tags','grep','export']:
        parsers[name].add_argument('--exclude-links',action='store_true',
            help='Do not include symlinked notefiles')

    # This sorts the optional arguments or each parser.
    # It is a bit of a hack. The biggest issue is that this happens on every 
    # call but it takes about 10 microseconds
    # Inspired by https://stackoverflow.com/a/12269358/3633154
    for parser in parsers.values():
        for action_group in parser._action_groups:
            # Make sure it is the **OPTIONAL** ones
            if not all(len(action.option_strings) > 0 for action in action_group._group_actions):
                continue
            action_group._group_actions.sort(key=lambda action: # lower of the longest key
                                                        sorted(action.option_strings,
                                                               key=lambda a:-len(a))[0].lower())
    
    args = parsers['main'].parse_args(argv)
    if args.debug:
        global DEBUG
        DEBUG = True
    if DEBUG: # May have been set not at CLI
        debug('argv: {}'.format(repr(argv)))
        debug(args)
    
    try:
        _handoff(args)
    except Exception as E:
        if DEBUG:
            raise
        print('ERROR: ' + str(E))
        sys.exit(1)
    
def _handoff(args):

    if getattr(args,'no_refresh',0) == getattr(args,'force_refresh',1) == True:
        raise ValueError('Cannot have no-refresh and force-refresh')
    
    if getattr(args,'no_refresh',False):
        args.hashfile = False
    
    ## Modification Actions
    if args.command == 'add':
        args.note = ' '.join(args.note)
        if args.note.strip() == '-':
            args.note = sys.stdin.read()
        
        add_note(args.file,args.note,
                 replace=args.replace,
                 link=args.link,
                 hashfile=args.hashfile)
        
        if not args.no_refresh:
            repair(args.file,repair_type='metadata',
                   force=args.force_refresh,link=args.link,
                   hashfile=args.hashfile)

    if args.command == 'edit':
        interactive_edit(args.file,link=args.link,hashfile=args.hashfile)
        if not args.no_refresh:
            repair(args.file,repair_type='metadata',
                   force=args.force_refresh,link=args.link,
                   hashfile=args.hashfile)

            
    if args.command == 'tag':
        for file in args.file:
            modify_tags(file,args.tag,remove=args.remove,link=args.link,hashfile=args.hashfile)
            if not args.no_refresh:
                repair(file,repair_type='metadata',
                       force=args.force_refresh,link=args.link,
                       hashfile=args.hashfile)
               
    if args.command == 'repair':
        repair(args.path,
               repair_type=args.type,
               dry_run=args.dry_run,
               force=args.force_refresh,
               link=args.link,
               excludes=args.exclude,
               matchcase=args.match_case,
               hashfile=args.hashfile,
               search_path=args.search_path,
               )

    ## Query Actions
    
    if args.command == 'cat':
        stream = sys.stdout if args.out_file is None else open(args.out_file,'wt') 
        cat(args.file,tags=args.tags,stream=stream,full=args.full)
        if args.out_file is not None:
            stream.close()
        
    if args.command == 'grep':
        stream = sys.stdout if args.out_file is None else open(args.out_file,'wt') 

        grep(args.path,'|'.join(args.expr),
               expr_matchcase=args.match_expr_case,
               excludes=args.exclude,matchcase=args.match_case,
               exclude_links=args.exclude_links,
               stream=stream)
        if args.out_file is not None:
            stream.close()
    
    if args.command == 'list-tags':
        stream = sys.stdout if args.out_file is None else open(args.out_file,'wt') 
        
        list_tags(args.path,args.tags,
              excludes=args.exclude,matchcase=args.match_case,
              exclude_links=args.exclude_links,
              stream=stream)
        
        if args.out_file is not None:
            stream.close()
            
    if args.command == 'export':
        stream = sys.stdout if args.out_file is None else open(args.out_file,'wt') 
        
        export(args.path,
              excludes=args.exclude,
              matchcase=args.match_case,
              exclude_links=args.exclude_links,
              stream=stream)
        
        if args.out_file is not None:
            stream.close()    
    
    
if __name__ == '__main__':
    cli()
