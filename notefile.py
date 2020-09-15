#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Write notesfiles to accompany main files
"""
from __future__ import division, print_function, unicode_literals
__version__ = '20200915.0'
__author__ = 'Justin Winokur'

import sys
import os
import shutil
import warnings
import copy
# Many imports are done lazily since they aren't always needed
    
# Third-Party
import ruamel.yaml
from ruamel.yaml.scalarstring import PreservedScalarString 

if sys.version_info[0] > 2:
    unicode = str

NOTESEXT = '.notes.yaml'
NOHASH = '** not computed **'
DT = 1 # mtime change

HIDDEN = os.environ.get('NOTEFILE_HIDDEN','false').strip().lower() == 'true'
DEBUG = os.environ.get('NOTEFILE_DEBUG','false').strip().lower() == 'true'

def debug(*args,**kwargs):
    if DEBUG:
        kwargs['file'] = sys.stderr
        print('DEBUG:',*args,**kwargs)

#### Set up YAML
yaml = ruamel.yaml.YAML()

def pss(item):
    """
    Convert strings with '\n' to PreservedScalarString
    and recurse into dicts and lists (and tuples which are converted to lists).
    """
    if isinstance(item,(list,tuple)):
        return [pss(i) for i in item]
    elif isinstance(item,dict):
        item = item.copy()
        for key,val in item.items():
            item[key] = pss(val)
        return item
    elif isinstance(item,(str,unicode)) and '\n' in item:
        return PreservedScalarString(item)
    else:
        return item

#### /Set up YAML

################################################################################
#################################### utils #####################################
################################################################################
def touni(s):
    if isinstance(s,(tuple,list)):
        return type(s)([touni(i) for i in s])
    try:
        return s.decode('utf8')
    except:
        pass
    return s

def randstr(N=10):
    import random # lazy import
    return ''.join(random.choice('abcefghijklmnopqrstuvwxyz0123456789') for _ in range(N))

def exists_or_link(filename):
    """
    exists will return false if a broken link. This will NOT
    """
    return os.path.isfile(filename) or os.path.islink(filename)

def now_string(pm=False):
    """
    print the current time with time zone
    
    if `pm=False` will print the time zone with '+' or '-'. Otherwise, will use
        '+' --> 'p'
        '-' --> 'n'
    
    From http://stackoverflow.com/a/1111655
    """
    import datetime,time
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
    Normalize filenames for NOTESEXT
    
    If given a hidden notefile, assumes the base name is 
    NOT hidden. 
    
    returns:
        filename,vis_note,hid_note
    """
    filename = touni(filename)
    base,name = os.path.split(filename)
    
    if name.endswith(NOTESEXT): # Given a notefile path
        if name.startswith('.'): # Given a HIDDEN file
            vis_note = name[1:]
            hid_note = name
            name = name[1:-len(NOTESEXT)] # Assume *NOT* hidden
        else:
            vis_note = name
            hid_note = '.' + name
            name = name[:-len(NOTESEXT)]
    else:
        if name.startswith('.'): # file itself is hidden
            vis_note = hid_note = name + NOTESEXT
        else:
            vis_note = name + NOTESEXT
            hid_note = '.' + vis_note
        
    return os.path.join(base,name),os.path.join(base,vis_note),os.path.join(base,hid_note)

def sha256(filepath,blocksize=2**20):
    """
    Return the sha256 hash of a file. 
    
    `blocksize` adjusts how much of the file is read into memory at a time.
    This is useful for large files.
        2**20: 1 mb
        2**12: 4 kb
    """
    import hashlib
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()

def hidden_chooser(notesfile,hnotesfile,hidden):
    """
    Simple util but I keep needing it. 
    
    Searches for an existing notefile searching in order of `hidden`.
    
    Retuns:
        notefilepath,<whether or not it exists>
    """
    testfiles = [hnotesfile,notesfile] if hidden else [notesfile,hnotesfile]
    for testfile in testfiles:
        if exists_or_link(testfile):
            return testfile,True
    return testfiles[0],False # first one from hidden

def tmpfileinpath(dirpath):
    if not os.path.isdir(dirpath):
        dirpath = os.path.dirname(dirpath)
    return os.path.join(dirpath,'.notefile.' + randstr(15))    

def exclude_in_place(mylist,excludes,
                     isdir=False,
                     matchcase=False,
                     remove_noteext=True,
                     keep_notes_only=None):
    """
    Helper tool to apply exclusions IN PLACE in mylist
    
    Options:
    --------
    isdir [False]
        Whether to also test for directories explicitly (trailing / on dirs)
    
    matchcase:
        Match case on exclusions
    
    remove_noteext [False]
        test and compare without NOTESEXT. Also assumes the main file
        does not have a . if the note is hidden
    
    keep_notes_only [None] {None,True,False}
        None: No Filters
        True: Removes *NON* notes
        False: Removes Notes
    
    """
    import fnmatch # Lazy
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
        if (keep_notes_only is False and item.endswith(NOTESEXT)) \
        or (keep_notes_only is True and not item.endswith(NOTESEXT)):
            mylist.remove(item)
            continue
        
        item0 = item
        if item.endswith(NOTESEXT) and remove_noteext:
            item = item[:-len(NOTESEXT)]
            if item.startswith('.'):
                item = item[1:]
            
            
        if any(fnmatch.fnmatch(case(item),e) for e in excludes):
            mylist.remove(item0)
            continue
        if isdir and any(fnmatch.fnmatch(case(item + '/'),e) for e in excludes):
            mylist.remove(item0)
            continue

  
def find_by_size_mtime_hash(path,size,mtime,sha,excludes=None,matchcase=False,maxdepth=None):
    """
    Find potential basefiles based on thier size and hash. Check sizes first and
    then only hash if the size matches.
    
    If mtime is None, will not check it
    """
    possible = []
    for root, dirs, files in os.walk(path):
        exclude_in_place(files,excludes,matchcase=matchcase,isdir=False)
        exclude_in_place(dirs,excludes,matchcase=matchcase,isdir=True)

        rel = os.path.relpath(root,path)
        depth = rel.count('/') + 1 if rel != '.' else 0
        if maxdepth is not None and depth > maxdepth:
            del dirs[:] # Do not go deeper
            continue

        files.sort(key=lambda s:s.lower())
        for file in files:
            file = os.path.join(root,file)
            
            if not os.path.exists(file): 
                continue # Likely a broken link
            
            stat = os.stat(file)
            
            if not stat.st_size == size:
                continue
            if mtime is not None and abs(mtime - stat.st_mtime) > DT:
                continue
            
            if sha256(file) == sha:
                possible.append(file)
    return possible


def symlink_file(src,dstdir):
    """
    Create a relative symlink from src to the dstdir. Note that the dest is
    a directory
    """
    dst = os.path.join(dstdir,os.path.basename(src))
    
    for i in range(1,100): # Really shouldn't need 100. Make this an upper limit for safety
        if not os.path.exists(dst):
            break
        dst0 = dst
        a,b = os.path.splitext(dst)
        dst = a + '.{}'.format(i) + b
        warnings.warn("'{dst0}' exists. Changing to '{dst}'".format(dst0=dst0,dst=dst))
    else:
        raise ValueError('Too many existing files with the same name')
    
    src = os.path.relpath(src,dstdir)
    
    try:
        os.makedirs(dstdir)
    except OSError:
        pass
    
    os.symlink(src,dst)
    debug("symlink '{}' --> '{}'".format(src,dst))
    
################################################################################
############################### Notefile Object ################################
################################################################################

class Notefile(object):
    """
    Main notes object
    
    Inputs:
    -------
    filename
        Filename (or notefile name). Will be set as needed
    
    hidden [Global default]
        Whether or not to *prefer* the hidden notefile
    
    link ['both']
        How to handle symlinks.
    
    hashfile [True]
        Whether or not to hash the file    
    
    Notable Attributes:
    -------------------
    Any attribute with 0 is the original. The version without 0 is the refferent
    if the file is a symlink and not 'symlink' mode
    
    filename0,filename: str
        File being noted
        
    destnote0,destnote: str
        The final note location.
    
    islink: bool
        Whether or not the note is a link. 
        
    hidden: bool
        Whether the note is hidden or not. May be different than the setting
        if the note already existed
    
    data:
        Note data including 'notes' and 'tags'. Note that you *must* call read()
        first
    
    Notable Methods:
    ---------------
    read()
        Read the contents of the note. Cannot use data without having called
        read()
    
    write()
        Write the note content. Many actions will change data but will not save
        it unless write() is called
    
    make_links()
        Build the appropriate symlinks if the note is a link
    
    Note:
    -----
    Most methods also return itself for convenience 
    """
    def __init__(self,filename,hidden=HIDDEN,link='both',hashfile=True):
        ## Notation: 
        #   _0 names re the original file for a link (or when 'symlink' mode).
        #   When not a link, it doesn't matter!
        self.hashfile = hashfile
        self.link = link
        
        self.filename,self.vis_note,self.hid_note = get_filenames(filename)
        
        if os.path.basename(self.filename).startswith('.'):
            warnings.warn("hidden files may not always work: '{}'".format(self.filename))
        
        # Store the original paths. Will be reset later if link 
        self.destnote0,_ = hidden_chooser(self.vis_note,self.hid_note,hidden)
        for attr in ['filename','vis_note','hid_note']:
            setattr(self,attr+'0',getattr(self,attr))
        
        ## Handle links. If both or source, reset to the referent if the link
        # mode cannot be deduced. If it can, use that!        
        if not link in {'both','symlink','source'}:
            raise ValueError("'link' must be in {'both','symlink','source'}")
        
        # Be False even if link for 'symlink' mode
        self.islink = os.path.islink(self.filename) and link in ['both','source'] 
        
        if self.islink:
            # Edge Case: Note created in symlink mode but isn't being modified
            # as such
            if os.path.isfile(self.destnote0) and not os.path.islink(self.destnote0):
                debug("'symlink' mode deduced. Changing mode")
                self.islink = False
            else:            
                dest0 = os.readlink(self.filename)
                dest = os.path.abspath(os.path.join(os.path.dirname(self.filename),dest0))
            
                self.islinkabs = dest == dest0
            
                debug("Linked Note: '{}' --> '{}'".format(self.filename,dest0))
            
                self.filename,self.vis_note,self.hid_note = get_filenames(dest)
        
        
        # Get the actual notefile path (destnote) regardless of hidden settings
        # And whether it exists
        self.destnote,self.exists = hidden_chooser(self.vis_note,self.hid_note,hidden)
        self.hidden = hidden
        self.ishidden = self.destnote0 == self.hid_note0
        debug('Hidden setting: {}. Is hidden: {}'.format(self.hidden,self.ishidden))
        
        # Check if orphhaned on original file (broken links are still NOT orphaned)
        self.orphaned = not exists_or_link(self.filename0)
        
        self.txt = None
        self.data = None
    
    def read(self,_sha256=None):
        """
        Read the note and store the data.
        """
        if self.exists:
            debug("loading {}".format(self.destnote))
            with open(self.destnote,'rt') as file:
                self.txt = file.read()
            self.data = yaml.load(self.txt)
        else:
            debug('New notefile')
            try:
                stat = os.stat(self.filename) 
            except Exception as E:
                if os.path.islink(self.filename0):
                    raise type(E)('Broken Link')
                raise # Shouldn't be here!!!
                
            self.data = {'filesize': stat.st_size,
                         'mtime':stat.st_mtime}
            if self.hashfile:
                self.data['sha256'] = sha256(self.filename)
            
            
        if 'tags' not in self.data:
            self.data['tags'] = []
            
        if 'notes' not in self.data:
            self.data['notes'] = ''
        
        # Make a copy for compare later. Use deep copy in case mutable 
        # objects are modified
        self.data0 = copy.deepcopy(self.data) 
        
        return self # for convenience
        
    def write(self,force=False):
        """
        Write the data
        """
        if self.data is None:
            raise ValueError('Cannot write empty data. Use read() or set data attribute')
        
        if 'notes' in self.data:
            self.data['notes'] = self.data['notes'].strip() 
        
        tags = self.data.get('tags',[])
        tags = set(t.strip() for t in tags if t.strip())
        self.data['tags'] = sorted(tags)
        
        data = pss(self.data) # Will recurse into lists and dicts too
        
        if not force and not self.ismod():
            debug('Note not modified. Not saving')
            self.make_links() # Rebuild the links in case they were broken
            return
            
        data['last-updated'] = now_string()
        data['notefile version'] = __version__
        
        try:
            data = ruamel.yaml.comments.CommentedMap(data)
            data.yaml_set_start_comment('YAML Formatted notes created with notefile version {}'.format(__version__))
        except TypeError:
            pass # Likely due to python2 and ordering
        
        # Make the write atomic
        tmpfile = tmpfileinpath(self.destnote)   
        with open(tmpfile,'wt') as file:
            yaml.dump(data,file)
        shutil.move(tmpfile,self.destnote)
        debug("Wrote '{}'".format(self.destnote))
        
        self.make_links()

        return self # for convenience
    def ismod(self):
        """
        Compare data0 (when read()) to data (before write())
        """
        # Will do a dictionary compare at the end so pop() certain keys before
        # we get to that. Since we're removing then, make a copy
        if not hasattr(self,'data0'):
            return True

        old,new = self.data0.copy(),self.data.copy()
        
        for key in ['last-updated','notefile version']:
            old.pop(key,None),new.pop(key,None)
       
        if abs(old.pop('mtime',0) - new.pop('mtime',100)) >= DT:
            return True
        
        old['tags'] = set(old.get('tags',[]))
        new['tags'] = set(new.get('tags',[]))
        
        return not old == new
        
    def make_links(self):
        """
        Build the links if the note is a link.
        """
        # Handle both-type links by linking to the note
        if self.islink and self.link == 'both':
            linknote = self.destnote0 # Original path for the note
            
            # Determine the symlink path 
            if self.islinkabs:
                linkpath = self.destnote
            else:
                linkpath = os.path.relpath(self.destnote,os.path.dirname(linknote))
            try:
                os.remove(linknote)
            except OSError:
                pass
                
            os.symlink(linkpath,linknote)
   
    def interactive_edit(self,full=False):    
        """Launch the editor. Does *NOT* write()"""
        import subprocess
        if self.data is None:
            raise ValueError('Cannot edit empty data. Use read() or set data attribute')
            
        editor_names = ['EDITOR','GIT_EDITOR','SVN_EDITOR','LOCAL_EDITOR']
        for editor_name in editor_names:
            try:
                editor = os.environ[editor_name]
                break
            except KeyError:
                pass
        else:
            raise ValueError(('Must specify an editor. Possible enviormental variables: '
                              ', '.join("'{}'".format(e) for e in editor_names)))
        
        tagtxt = '<< Comma-seperated tags. DO NOT MODIFY THIS LINE >>'
        
        if full:
            self.data2txt()
            content = self.txt
        else:
            content = self.data.get('notes','')
            content += '\n\n' + tagtxt + '\n'
            tags = self.data.get('tags',[])
            tags = sorted(t for t in set(tt.strip().lower() for tt in tags) if t)
            content += ', '.join(tags) + '\n'
        
        tmpfile = tmpfileinpath(self.destnote)
        with open(tmpfile,'wt') as file:
            file.write(content)

        subprocess.check_call([editor,file.name])

        with open(tmpfile,'rt') as f:
            newtxt = f.read()
        os.remove(tmpfile)
        
        if full:
            self.data = yaml.load(newtxt)
        else:
            lines = iter(newtxt.strip().split('\n'))
            note,tags = [],[]
            
            for line in lines: # Get notes
                if line.strip() == tagtxt:
                    break
                note.append(line)
            for line in lines: # Get tags with the remaining lines
                tags.extend(line.split(','))
                
            self.data['notes'] = '\n'.join(note)
            tags = sorted(t for t in set(tt.strip().lower() for tt in tags) if t)
            self.data['tags'] = tags
            
        return self # for convenience
    
    def add_note(self,note,replace=False):
        """Add (or replace) a note. Does *NOT* write()"""
        if self.data is None:
            raise ValueError('Cannot edit empty data. Use read() or set data attribute')

        if replace:
            self.data['notes'] = note
        else:
            self.data['notes'] += '\n' + note.strip()
        
        return self # for convenience
        
    def modify_tags(self,add=tuple(),remove=tuple()):
        """
        Add or remove tags. Does *NOT* write().
        
        Inputs:
        -------
        add [empty tuple]
            Iterable or str/unicode of tags to add
        
        remove [empty tuple]
            Iterable or str/unicode of tags to remove
        
        """
        tags = set(tag.lower() for tag in self.data.get('tags',[])) # make a mutable set
        
        if isinstance(add,(str,unicode)):
            add = [add] # make a list
        if isinstance(remove,(str,unicode)):
            remove = [remove] # make a list
            
        tags.difference_update(remove)
        tags.update(add)
        self.data['tags'] = sorted(t.lower().strip() for t in tags if t.strip())
    
    
    def cat(self,tags=False,full=False):
        """cat the notes to a string"""
        if self.data is None:
            raise ValueError('Cannot edit empty data. Use read() or set data attribute')

        if full:
            self.data2txt()
            return self.txt
            
        if tags:
            tags = self.data.get('tags',[])
            tags = sorted(t.lower() for t in tags)
            return '\n'.join(tags)
            
        return self.data.get('notes','')
        
    def data2txt(self):
        """
        Fills the text attribute
        """
            
        if sys.version_info[0] == 2: # Issues with the io.StringIO in py2
            debug('Dammit! Switch to python3 already! Writing then reading')
            warnings.warn('python2 will be deprecated shortly')
            self.write()
            self.read()
            return self.txt
        
        import io
        f = io.StringIO()
        yaml.dump(self.data,f)
        self.txt = f.getvalue()
        return self.txt
        
    def repair_metadata(self,dry_run=False,force=False,stream=sys.stdout):
        """
        Repair (if Needed) the notefile metadata.
        
        If force, will check (mtime,size) and reset as needed.
        Otherwise, will first check (mtime,size). If they are wrong, will update
        them and the sha256 if self.hashfile
        
        dry_run will *not* update anything
        
        does *NOT* write!
        """
        if self.data is None:
            raise ValueError('Cannot edit empty data. Use read() or set data attribute')
        # This is designed to be called before reading, etc for orphaned
        if not os.path.exists(self.filename):
            raise ValueError('File is orphaned')
        
        stat = os.stat(self.filename)
        
        if force \
        or self.data.get('filesize',-1) != stat.st_size  \
        or abs(self.data.get('mtime',-1) - stat.st_mtime) > DT \
        or self._isbroken_broken_from_hide():
            if dry_run:
                return True # Do not do anything else since we won't be writing
            
            self.data['filesize'] = stat.st_size
            self.data['mtime'] = stat.st_mtime
            if self.hashfile:
                self.data['sha256'] = sha256(self.filename)
            
            return True    
        
        return False
    
    def _isbroken_broken_from_hide(self):
        """
        Returns whether a link note is broken from being hidden
        """
        if self.link != 'both' or not self.islink:
            return False
        
        # Is it a link and is it NOT broken (is a file)
        if os.path.islink(self.destnote0) and os.path.isfile(self.destnote0):
            return False
        
        # Finally make sure the *correct* dest exists:
        if not os.path.isfile(self.destnote):
            return False # Still broken but not repairable
        
        return True

################################################################################   
################################## functions ###################################
################################################################################   
def copy_note(src,dst,
              noteopts=None):
    """
    copy from src to dst
    
    Inputs:
    -------
    src,dst
        Source and Dest. Dest must not have ANY notes
    
    noteopts [{}]
        Options for the new note
    """
    if noteopts is None:
        noteopts = {}
    dst_note = Notefile(dst,**noteopts)
    if exists_or_link(dst_note.destnote0) or exists_or_link(dst_note.destnote):
        raise ValueError("Cannot copy notes to '{}' since it has notes already".format(dst_note.filename0)) 
    dst_note.read() # Will set metadata, etc
    
    src_note = Notefile(src) # SRC is assumed to have it's OWN notefile (symlink or file)
    src_note.read()
    
    # Copy all NEW keys from src and dst. Delete notes and tags so they are
    # also copied
    del dst_note.data['tags']
    del dst_note.data['notes']
    
    for key,val in src_note.data.items():
        if key in dst_note.data or key == 'sha256':
            continue # things like metadata
        dst_note.data[key] = val
    
    dst_note.write()


def _dot_sort(file):
    file = file.lower()
    if file.startswith('.'):
        return file[1:]
    return file

def find_notes(path='.',
               excludes=None,matchcase=False,
               maxdepth=None,
               exclude_links=False,
               include_orphaned=False,
               return_note=False,
               noteopts=None):
    """
    find notes recurisvly starting in `path`
    
    Options:
    --------
    path ['.']
        Where to look. If given as a specific file, will
        ignore include_orphaned. 
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0
    
    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded   
    
    return_note [False]
        Return the note object
    
    noteopts [{}]
        Options for the notefile created and returned
    
    Yields:
    -------
    note
        Either filename or Notefile object
    
    """
    if noteopts is None:
        noteopts = {}
     
    if os.path.isfile(path):
        nf = Notefile(path,**noteopts)
        yield nf if return_note else nf.destnote0
        return
    
    for root, dirs, files in os.walk(path):        
        exclude_in_place(files,excludes,matchcase=matchcase,isdir=False,
                         remove_noteext=True,keep_notes_only=True) # We are *only* looking for notes
        exclude_in_place(dirs,excludes,matchcase=matchcase,isdir=True)
        
        rel = os.path.relpath(root,path)
        depth = rel.count('/') + 1 if rel != '.' else 0
        if maxdepth is not None and depth > maxdepth:
            del dirs[:] # Do not go deeper
            continue

        files.sort(key=_dot_sort)
        dirs.sort(key=lambda s:s.lower())
        
        for file in files:
            if not file.lower().endswith(NOTESEXT):
                continue
                
            ffile = os.path.join(root,file)
            
            nf = Notefile(ffile,**noteopts)
            if exclude_links and nf.islink:
                continue
            
            if nf.orphaned and not include_orphaned: 
                continue
            
            yield nf if return_note else nf.destnote0

    ## TODO: Are link notes orphaned if they are too?

def grep(path='.',expr='',
         expr_matchcase=False,
         excludes=None,matchcase=False,
         maxdepth=None,
         exclude_links=False,include_orphaned=False,
         full_note=False,full_word=False,
         fixed_strings=False,
         match_any=True,
         symlink_result=None):
    """
    Search the content of notes for expr
    
    Inputs:
    -------
    path ['.']
        Where to search
    
    expr ['']
        Expression to search. Can be regex. Also can pass a tuple or list
    
    expr_matchcase [False]
        Whether or not to consider case in the expression
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded   
    
    full_note [False]
        Whether to search the entire note text or just the "notes" section
    
    fixed_strings [False]
        Match the string exactly. i.e. does a re.escape() on the pattern
    
    full_word [False]
        If True, matches the full word. Basically add \b to each pattern
    
    match_any [True]
        Whether to match any expr

    symlink_result [None]
        If specified, will make symlinks in '<symlink_result>'
    
    Yields:
    -------
    filename
        Filename of matches
    """
    import re
    flags = re.MULTILINE | re.UNICODE
    if not expr_matchcase:
        flags = flags | re.IGNORECASE
    if isinstance(expr,(str,unicode)):
        expr = (expr,)
    
    if fixed_strings:
        expr = [re.escape(e) for e in expr]
    
    if full_word:
        expr = [r'\b' + e + r'\b' for e in expr]
    
    # For all, you need individual regexes but for any, can make a single one
    if match_any:
        requery = re.compile('|'.join(expr),flags=flags)
        query = lambda qtext: bool(requery.search(qtext))
    else:
        requeries = [re.compile(e,flags=flags) for e in expr]
        query = lambda qtext: all(r.search(qtext) for r in requeries)
    
    notes = find_notes(path=path,
                       excludes=excludes,matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=include_orphaned,
                       return_note=True) # no need to send noteopts
    
    def _sym(src):
        if symlink_result:
            symlink_file(src,symlink_result)
        return src
    
    # If the results will be symlinked, we want to have already traversed
    # so run this now
    if symlink_result:
        notes = list(notes)
    
    for note in notes:
        # Since reading the YAML is slow, we query the note itself.
        # If full_mode, we're done. Otherwise, we then read the YAML and
        # apply the query again
                
        with open(note.destnote,'rt') as f:
                qtext = f.read()
        
        if not query(qtext):
            continue
                        
        if full_note:
            yield _sym(note.filename0) # non-link version
            continue
            
        note.read()
        qtext = note.data.get('notes','')
        if query(qtext):
            yield _sym(note.filename0) # non-link version

class QueryError(ValueError):
    pass

def query(path='.',
          expr=None,
          expr_matchcase=False,
          excludes=None,matchcase=False,
          maxdepth=None,
          exclude_links=False,
          include_orphaned=False, 
          full_word=False,fixed_strings=False,
          symlink_result=None):
    """
    Perform python queries on notes:
    
    Inputs:
    -------
    path ['.']
        Where to search
    
    expr ['']
        Query expression. See query_help() for details
    
    expr_matchcase [False]
        Whether or not to consider case in grep function
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded   
    
    fixed_strings [False]
        Match the string exactly for grep. i.e. does a re.escape() on the pattern
    
    full_word [False]
        If True, matches the full word. Basically add \b to each pattern

    symlink_result [None]
        If specified, will make symlinks in '<symlink_result>'
    
    Yields:
    -------
    filename
        Filename of matches
    
    """
    # Lazy imports      
    import re
    from functools import partial
    
    flags = re.MULTILINE | re.UNICODE
    if not expr_matchcase:
        flags = flags | re.IGNORECASE
    
    if isinstance(expr,(str,unicode)):
        expr = (expr,)

    def _grep(expr,note=None):
        if fixed_strings: expr = re.escape(expr)
        if full_word: expr = r'\b' + expr + r'\b'
        return bool(re.search(expr,note,flags=flags))
    
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=include_orphaned,
                       return_note=True) # no need to send noteopts
    
    # If the results will be symlinked, we want to have already traversed
    # so run this now
    if symlink_result:
        notes = list(notes)
    
    for note in notes:
        note.read()
        note.write = lambda *a,**k:None # disable write
        
        note.data['tags'] = set(t.lower() for t in note.data.get('tags',[]))
        
        namespace = {
            'note':note,
            'data':note.data,
            'tags':note.data['tags'],
            'notes':note.data.get('notes',''),
            'text':getattr(note,'txt',''),
        }
        namespace['grep'] = partial(_grep,note=namespace['notes'])
        namespace['g'] = namespace['grep']
        namespace['re'] = re
        
        full_expr = [i.strip() for e in expr for i in e.split(';') if i.strip()]
        full_expr[-1] = '_res = ' + full_expr[-1]
            
        for ii,line in enumerate(full_expr):
            try:
                exec(line,namespace)
            except Exception as E:
                err = E.__class__.__name__
                desc = unicode(E) 
                etxt = 'Line {} `{}` raised {}. MSG: "{}"'.format(ii,line,err,desc)
                raise  QueryError(etxt)
        
        if not bool(namespace['_res']):
            continue

        if symlink_result:
            symlink_file(note.filename0,symlink_result) # use the non-link version
        
        yield note.filename0

def search_tags(path='.',tags=tuple(),
                excludes=None,matchcase=False,
                maxdepth=None,
                exclude_links=False,include_orphaned=False,
                match_any=True,
                symlink_result=None):
    """
    Search notes for tags
    
    Inputs:
    -------
    path ['.']
        Where to search
    
    tags [tuple()]
        Tag or tags to search. Can be multiple or single. If empty,
        lists all
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directories with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded   
    
        
    match_any [True]
        Whether to match any expr
    
    symlink_result [None]
        If specified, will make symlinks in '<symlink_result>/<tag>'
    
    Returns:
    -------
    Dictionary of tags
    """
    from collections import defaultdict
    if isinstance(tags,(str,unicode)):
        tags = (tags,)
    
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=include_orphaned,
                       return_note=True) # no need to send noteopts)
    qtags = set(t.lower() for t in tags)
    match = any if match_any else all
    res = defaultdict(list)
    
    for note in notes:
        note.read()
        
        ntags = note.data.get('tags',[])
        ntags = set(t.lower() for t in ntags)
        
        if len(qtags) == 0: # No query, add them ALL
            for t in  ntags:
                res[t].append(note.filename0)
            continue
            
        # Test and then add each one
        if match(qtag in ntags for qtag in qtags):
            for t in qtags.intersection(ntags):
                res[t].append(note.filename0)
        
    res =  {k:sorted(res[k]) for k in sorted(res)}

    if symlink_result:
        for k,files in res.items():
            dstdir = os.path.join(symlink_result,k)
            for file in files:
                symlink_file(file,dstdir)
    return res

def change_tag(oldtag,newtag,
                path='.',
                excludes=None,matchcase=False,
                maxdepth=None,
                exclude_links=False,include_orphaned=False,
                dry_run=False,
                noteopts=None):
    """
    Search for oldtag and rename it newtag
    
    Inputs:
    -------
    oldtag,newtag
        The old and new tag names
        
    path ['.']
        Where to search
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directories with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded   
    
    noteopts [ None ]
        Options to pass to find_notes
    
    Yields:
    -------
    note - read and written note that was modified
    """
    
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=include_orphaned,
                       return_note=True,
                       noteopts=noteopts)

    oldtag,newtag = oldtag.lower().strip(),newtag.lower().strip()
    for note in notes:
        note.read()
        
        ntags = note.data.get('tags',[])
        ntags = set(t.lower() for t in ntags)

        if oldtag in ntags:
            if not dry_run:
                note.modify_tags(add=newtag,remove=oldtag)
                note.write()
            yield note
    
        
    

    
def export(path='.',
           excludes=None,matchcase=False,
           maxdepth=None,
           exclude_links=False,include_orphaned=False):
    """
    Return a single dictionary including a list of all notes 
    that can be later dumped.
    
    Inputs:
    --------
    path ['.']
        Where to look
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded       
    
    
    """       
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=include_orphaned,
                       return_note=True) # no need to send noteopts)
    
    res = {}
    res['description'] = 'notefile export'
    res['time'] = now_string()
    res['notefile version'] = __version__
    res['notes'] = {}
    
    for note in notes:
        note.read()
        res['notes'][note.filename0] = pss(note.data)
    
    try:
        res = ruamel.yaml.comments.CommentedMap(res)
        res.yaml_set_start_comment('YAML Formatted notefile export')
    except TypeError:
        pass # Likely due to python2 and ordering
    
    return res

def change_visibility(mode,
                      path='.',
                      dry_run=False,
                      excludes=None,matchcase=False,
                      maxdepth=None,
                      exclude_links=False,
                      include_orphaned=False):
    """
    Inputs:
    --------
    mode 
        Specify 'hide' or 'show'
    
    path ['.']
        Where to look
    
    dry_run [False]:
        Do not actually repair
        
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    include_orphaned [ False ]
        If True, will ALSO return orphaned notes. 
        Otherwise, they are excluded     
    
    Yields:
    ------
    name of changed noted if and only if the mode was changed
        
    Note: This is a generator so must be iterated to perform actions
    """      
    if mode not in {'hide','show'}:
        raise ValueError("Mode must be 'hidden','visible'")
        
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=False,
                       return_note=True) # no need to send noteopts)
    
    for note in notes:
        # Use the _0 versions since we want the link itself
        # if given
        vis_note,hid_note = note.vis_note0,note.hid_note0
        
        # This will raise an error *no matter the current state*
        # by design
        if os.path.exists(vis_note) and os.path.exists(hid_note):
            warnings.warn("Both hidden and visible notes exist for '{}'. Not changing mode".format(note.filename0))
            continue
        if mode == 'hide':
            src_note = vis_note
            dst_note = hid_note
        else:
            src_note = hid_note
            dst_note = vis_note
        
        if not dry_run:
            try:
                shutil.move(src_note,dst_note)
            except (OSError,IOError): 
                continue
        yield note.filename0
        
        
    

################################################################################   
################################### Repair #####################################
################################################################################ 
def repair_orphaned(path='.',
                    dry_run=False,
                    excludes=None,matchcase=False,
                    maxdepth=None,
                    exclude_links=False,
                    check_mtime=False,
                    search_path=None,search_maxdepth=None,
                    noteopts=None,
                    hidden=HIDDEN):
    """
    Find orphaned notes and search for thier original refferent. 
    
    Note that hidden status is based on source status
    
    Inputs:
    --------
    path ['.']
        Where to look
    
    dry_run [False]:
        Do not actually repair
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    check_mtime [False]
        If True, will require mtime to not be changed
    
    search_path [path]
        Where to search for the original file. Note that the search will use
        the same excludes and matchcase but can set its own depth
    
    search_maxdepth [maxdepth]
        Maximum depth for searching search_path
        
    noteopts [{}]
        Options passed to Notefile
    
    Yields:
    ------
    prev,new,<whether it actually was moved>
    
    Note: This is a generator so must be iterated to perform actions
    """
    if search_path is None:
        search_path = path
    if search_maxdepth is None:
        search_maxdepth = maxdepth
    if noteopts is None:
        noteopts = {}
        
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=True,
                       return_note=True,
                       noteopts=noteopts)
    
    notes = (note for note in notes if note.orphaned)
    for note in notes:
        note.read()
        
        # handle if the hash is not the same caps
        data = {k.lower():v for k,v in note.data.items()}
        sha = data.get('sha256','')
        mtime = data.get('mtime',0) if check_mtime else None
        if len(sha) != 64 or 'filesize' not in data:
            warnings.warn("No SHA256 or filesize for '{}'. Cannot repair!".format(note.destnote0))
            continue
        
        candidates = find_by_size_mtime_hash(search_path,data['filesize'],mtime,sha,
                                       excludes=excludes,matchcase=matchcase,
                                       maxdepth=search_maxdepth)
        
        if len(candidates) > 1:
            wtxt = "{} candidates found for '{}'. Not repairing".format(len(candidates),note.destnote0)
            wtxt += '\n   '.join([''] + candidates)
            warnings.warn(wtxt)
            continue
        elif len(candidates) == 0:
            warnings.warn("No match for '{}'".format(note.destnote0))
            continue
            
        newfile = candidates[0]
        
        filename,notesname,hid_note = get_filenames(newfile)
        newnote,_ = hidden_chooser(notesname,hid_note,note.ishidden) # Respect the original note
        
        if dry_run:
            yield note.destnote0,newnote,False
            continue
        
        if os.path.exists(newnote):
            warnings.warn('Notefile exists. Not Moving!\n   SRC:{}\n   DST:{}'.format(note.destnote0,newnote))
            continue
            
        shutil.move(note.destnote0,newnote)
        yield note.destnote0,newnote,True
        
def repair_metadata(path='.',
                    dry_run=False,
                    force=False,
                    excludes=None,matchcase=False,
                    maxdepth=None,
                    exclude_links=False,
                    noteopts=None):
    """
    Find orphaned notes and search for thier original refferent.
    
    Inputs:
    --------
    path ['.']
        Where to look
    
    dry_run [False]:
        Do not actually repair
    
    force [False]
        Force a repair, including sha1
    
    excludes []
        Specify excludes in glob-style. Will be checked against
        both filenames and directories. Will also be checked against
        directorys with "/" appended
    
    matchcase [False]
        Whether or not to match the case of the exclude file
    
    maxdepth [None]
        Specify a maximum depth. The current directory is 0

    exclude_links [ False ] 
        If True, will *not* return symlinked notes
    
    noteopts [{}]
        Options passed to Notefile
    
    Yields:
    -------
    Name of repaired notes    
    
    Note: This is a generator so must be iterated to perform actions
    """
    if noteopts is None:
        noteopts = {}
    notes = find_notes(path=path,
                       excludes=excludes,
                       matchcase=matchcase,
                       maxdepth=maxdepth,
                       exclude_links=exclude_links,
                       include_orphaned=True,
                       return_note=True,
                       noteopts=noteopts)
   
    for note in notes:
        try:
            note.read()
        except (OSError,IOError):
            warnings.warn("Cannot stat '{}'. Likely a broken link. Repair manually!".format(note.filename0))
            continue
            
        try:
            if note.repair_metadata(dry_run=dry_run,force=force):
                if not dry_run:
                    note.write(force=True)
                yield note.destnote0
        except ValueError:
            continue # Orphaned
            
def query_help(print_help=True):
    help = """\
Queries:
--------
Queries are single expression statements that evaluate to True or False and
based on the note. It is evaluated as Python (with no sandboxing or sanitizing
so do not evaluate untrusted input). The following variables are defined:

    note    Notefile object including attributes such as 'filename',
            'destnote','hidden', etc. See Notefile documention
    data    Dictionary of the note
    notes   == data['notes']. The note text
    tags    == data['tags']. Set of tags (note, all lower case)
    text    Raw YAML of the note

And it includes the following functions:

    grep    performs a match against 'notes'. Respects the flags:
            '--match-expr-case','--fixed-strings','--full-word' automatically
    g       Aliased to grep

It also includes the `re` module

Queries can replace search-tags and grep but grep is much faster if it can
be used since it is accelerated by not parsing YAML unless needed.

For example, the following return the same thing:

    $ notefile grep word1 word2 
    $ notefile query "grep('word1') or grep('word2')"    

However, queries can be much more complex. For example:

    $ notefile query "(grep('word1') or grep('word2')) and not grep('word3')"

Limited multi-line support exists. Multiple lines can be delineated by separate
arguments and/or ';'. However, the last line must evaluate the query. Example:

    $ notefile query "tt = ['a','b','c']" "all(t in tags for t in tt)"

Queries are pretty flexible and give a good bit of control but some actions
and queries are still better handled directly in Python.

Reminder: Do not query untrusted input!
"""
    if print_help:
        print(help)
    return help
    
def cli(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    
    if len(argv)==0 or argv[0] == 'help':
        argv = ['-h']
        
    description = """\
notefile -- Tool for managing notes, tags, etc in 
            associated *{} files""".format(NOTESEXT)
    epilog ="""\
Notes:

* The hidden and visible settings are for creating notes. The setting is
  ignored if either a hidden or visible note already exits. If both exist,
  it will use the setting (and depending on the use, may throw an 
  error/warning)
  
* metadata is refreshed if mtime or size have changed.
  Or if `--force-refresh` and never if `--no-refresh`

* If there exists *different* notefiles for a symlink and its source, 
  the notefile may be overwritten if `--link` is not set properly. 
  Use caution!
    
"""





    import argparse
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
        help='Replace rather than append the new note')
        
    parsers['edit'] = subpar.add_parser('edit',
        help="Launch $EDITOR to interactivly edit the notes for a file") 
    parsers['edit'].add_argument('file',help='Specify file to edit')
    
    parsers['tag'] = subpar.add_parser('tag',
        help="Add or remove tags from file. Note that tags are converted to lowercase") 
    parsers['tag'].add_argument('-r','--remove',default=[],
        action='append',help='Specify tags to remove')
    parsers['tag'].add_argument('-t','--tag','-a','--add',default=[],
        action='append',help='Specify tags to add')
    parsers['tag'].add_argument('file',help='File(s) to tag',nargs='+')

    parsers['copy'] = subpar.add_parser('copy',
        help="Copy the notes from SRC to DST. DST must NOT have any notes.") 
    parsers['copy'].add_argument('SRC',
        help=("Source file. If a link, must have it's OWN notefile or link to a "
              "notefile (i.e. not created with 'source' mode)"))
    parsers['copy'].add_argument('DST',help='Destination file. Must not have ANY notes')
    
        
    parsers['repair'] = subpar.add_parser('repair',
        help=("Verify basefile and metadata. Note that unless `--force-refresh`, "
              "files with matching mtime and size are *NOT* rehashed. "))
    parsers['repair'].add_argument('path',nargs='?',default='.',
        help=("['.'] Specify the path to repair. If PATH specific file, will only "
              'repair that file. If PATH is a directory, will recursivly repair all items. '
              'Will only grep in or below the *current* directory for orphaned files.'))
    parsers['repair'].add_argument('-t','--type',choices=['both','metadata','orphaned'],
        default='both',
        help=("['both'] Specify the type of repairs to make. Metadata repairs only fix the "
              "metadata for the base file (and only checks the hash if other metadata "
              "is wrong or if `--force-refresh`). Orphaned repairs look in --search-path for "
              "an orphaned basefile. The search is optimized by searching by size "
              "(and optionally mtime) first before hashing"))
    parsers['repair'].add_argument('--search-path',default='.',metavar='PATH',
        help=('[%(default)s] Specify the path to search for the basefile for '
              'orphaned notefiles. WARNING: Will recurse the _entire_ path '
              'which may be very slow for large directories'))
    parsers['repair'].add_argument('-m','--mtime',action='store_true',
        help=('Require mtime be the same for orphaned notes. Could speed '
              'up search by reducing the number of files to be hashed'))
    
    parsers['change_tag'] = subpar.add_parser('change-tag',help='Change one tag to another')
    parsers['change_tag'].add_argument('old_tag',help='Old tag you will be changing')
    parsers['change_tag'].add_argument('new_tag',help='New tag you will be using')
    parsers['change_tag'].add_argument('-s','--silent',action='store_true',
        help='Do NOT list notes that were modified')
    
    
    ## Queries
    parsers['cat'] = subpar.add_parser('cat',help="Print the notes")
    parsers['cat'].add_argument('file',help='Specify file to cat')
    parsers['cat'].add_argument('-t','--tags',action='store_true',
        help='Print tags rather than notes') 
    
    parsers['find'] = subpar.add_parser('find',help="Find and list all notes")

    parsers['grep'] = subpar.add_parser('grep',help="Search notes for a given string")
    parsers['grep'].add_argument('expr',nargs='+',
        help=('Search expression. Follows python regex patterns (unless -F). '
              'Multiple arguments are considered an ANY query unless --all is set. '
              'Use advanced regex strings for more control. May need to escape them for bash parsing'))    
    parsers['grep'].add_argument('-f','--full',action='store_true',
        help='Search all fields of the note rather than just the "notes" field')

    
    parsers['query'] = subpar.add_parser('query',help="Advanced queries on notes",
                                         epilog=query_help(print_help=False),
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    parsers['query'].add_argument('expr',nargs='+',
        help=("Query expression. See 'query -h' for details. Can be multiple lines "
              "delineated by multiple arguments and/or ';' but the last line must "
              "evaluate to True or False as the query"))

    parsers['search_tags'] = subpar.add_parser('search-tags',
        help=("List all files with the specific tag(s) or all tags. "
              "Always outputs in YAML format"))
    parsers['search_tags'].add_argument('tags',nargs='*',
        help=('Specify tag(s) to list. If empty, lists them all. '
              'Multiple arguments are considered an ANY query unless --all is set.'))
    parsers['search_tags'].add_argument('--filter',action='store_true',help=argparse.SUPPRESS)
    parsers['search_tags'].add_argument('-t','--tag-only',action='store_true',
        help=('Print just the tag names and not the files'))   
    
    parsers['export'] = subpar.add_parser('export',help="Export all notesfiles to YAML")
    
    parsers['vis'] = subpar.add_parser('vis',help='Change the visibility of file(s)/dir(s)')
    parsers['vis'].add_argument('mode',choices=['hide', 'show'],
        help='Visibility mode for file(s)/dir(s) ')
    parsers['vis'].add_argument('path',default=['.'],nargs='*',help='[.] files(s)/dir(s)')

    ## Common arguments for when there are more than one command using it
    # Could use various parent parsers but this is honestly just as easy!
    
    # Modification Flags. 
    for name in ['add','edit','tag','repair','copy','change_tag']:
        parsers[name].add_argument('--no-hash',action='store_false',dest='hashfile',
            help='Do *not* compute the SHA256 of the basefile. Will not be able to repair orphaned notes')
        parsers[name].add_argument('--link',choices=['source','symlink','both'],
            default='both',
            help=("['%(default)s'] Specify how to handle symlinks. "
                  "If 'source', will add the notefile to the source only (non-recursively). "
                  "If 'symlink', will add the notefile to *just* the symlink file. "
                  "If 'both', will add the notefile the source (non-recursivly) and then symlimk to that notefile"))
        
        if name == 'copy': # Neither of these make sense with copy
            continue
        
        parsers[name].add_argument('--force-refresh',action='store_true',
            help='Force %(prog)s to refresh the metadata of files when the notefile is modified')
        
        if name == 'repair': # no-refresh doesn't make sense with repair
            continue
        
        parsers[name].add_argument('--no-refresh',action='store_true',
            help='Never refresh file metadata when a notefile is modified')

    # Search path
    for name in ['change_tag', 'export', 'find', 'grep', 'query', 'search_tags']:
        parsers[name].add_argument('-p','--path',default='.',help='[%(default)s] Specify path')
    
    # grep and query:
    for name in ['grep','query']:
        parsers[name].add_argument('--match-expr-case',action='store_true',dest='match_expr_case',
            help='Match case on grep expression')
        parsers[name].add_argument('-F','--fixed-strings',action='store_true',
            help='Match the string literally without regex patterns for grep expression')
        parsers[name].add_argument('--full-word',action='store_true',
            help='Matches the full word(s) of the grep expression. (adds \b)')
        
    # Hidden settings ( Repair hidden respects source hidden)
    # Note that change_tag will only work on existing so no need to set hidden
    for name in ['add', 'copy', 'edit', 'tag']:
        parsers[name].add_argument('-H','--hidden',action='store_true',default=HIDDEN,
            help='Override default and make new notes hidden')
        parsers[name].add_argument('-V','--visible',action='store_false',dest='hidden',
            help='Override default and make new notes visible')
    
    # Add exclude options:
    for name in  ['change_tag', 'export', 'find', 'grep', 'query', 'repair', 'search_tags', 'vis']:
        parsers[name].add_argument('--exclude',action='append',default=[],
            help=('Specify a glob pattern to exclude when looking for notes. '
                  "Directories are also matched with a trailing '/'. Can specify multiple times."))
        parsers[name].add_argument('--match-exclude-case',action='store_true',
            dest='match_case',help='Match case on exclude patterns')
        parsers[name].add_argument('--max-depth',
            type=int,metavar='N',default=None,dest='maxdepth',
            help='Specify the maximum depth to search for notefiles. The current directory is 0')
        
        if name == 'repair': continue
        parsers[name].add_argument('--exclude-links',action='store_true',
            help='Do not include symlinked notefiles')
    
    # Queries
    for name in ['grep','search_tags']:
        parsers[name].add_argument('--all',action='store_false',dest='match_any',
                                   help='Match ALL expressions')        

    # add outfiles
    for name in ['search_tags','cat','grep','query','export','find','change_tag']:
        parsers[name].add_argument('-o','--out-file',help='Specify file rather than stdout',metavar='FILE')
        
    # dry run
    for name in ['repair','vis','change_tag']:
        parsers[name].add_argument('--dry-run',action='store_true',
            help='Do not make any changes')

    # Null print0
    for name in ['find','grep','query']:
        parsers[name].add_argument('-0','--print0',action='store_true',
        help=("Terminate lines with a nul byte for use with `xargs -0` when "
              "filenames have spaces"))

    # full file
    for name in ['cat','edit']:
        parsers[name].add_argument('-f','--full',action='store_true',
            help='Prints/Edits the entire YAML notefile') 

    # symlink results
    for name in ['find','grep','search_tags','query']:
        parsers[name].add_argument('--symlink',default=None,metavar='DIR',
            help=('Create symlinks in DIR to the found files. If used in '
                  'search-tags, will also have subdirs with the name (or filter). '
                  'If there are name conflicts, will add `.N` to the filename '
                  'and print a warning to stderr'))


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
    
    # TMP
    if getattr(args,'filter',False):
        print('ERROR: --filter has been removed. Use query instead')
        sys.exit(1)
    
    global DEBUG
    if args.debug:
        DEBUG = True
    else:
        DEBUG = False
        
    if DEBUG: # May have been set not at CLI
        debug('argv: {}'.format(repr(argv)))
        debug(args)
    else:
        # Monkey patch warnings.showwarning for CLI usage
        warnings.showwarning = showwarning
        
    try:
        cliactions(args)        
    except Exception as E:
        if DEBUG:
            raise
        print('ERROR: ' + str(E))
        sys.exit(1)

def showwarning(*args,**kwargs):
   print('WARNING',unicode(args[0]),file=sys.stderr)
 
def cliactions(args):
    """Actually do the CLI work"""
    if getattr(args,'no_refresh',0) == getattr(args,'force_refresh',1) == True:
        raise ValueError('Cannot have no-refresh and force-refresh')
    
    if getattr(args,'no_refresh',False):
        args.hashfile = False # Reset this!
    
    # Store common settings with sensible defaults
    noteopts = dict(hidden=getattr(args,'hidden',None),
                    link=getattr(args,'link','both'),
                    hashfile=getattr(args,'hashfile',None))
    
    findopts = dict(path=getattr(args,'path',None),
                    excludes=getattr(args,'exclude',None),
                    matchcase=getattr(args,'match_case',False),
                    maxdepth=getattr(args,'maxdepth',None),
                    exclude_links=getattr(args,'exclude_links',False),
                    )
    
    ## Modification Actions
    if args.command == 'add':
        args.note = ' '.join(args.note)
        if args.note.strip() == '-':
            args.note = sys.stdin.read()        
        
        note = Notefile(args.file,**noteopts)      
        note.read()
        
        note.add_note(args.note,replace=args.replace)
        if not args.no_refresh:
            note.repair_metadata(force=args.force_refresh)
        note.write()
        
    if args.command == 'edit':      
        note = Notefile(args.file,**noteopts)
        note.read()
        note.interactive_edit(full=args.full)
        if not args.no_refresh:
            note.repair_metadata(force=args.force_refresh)
        note.write()
           
    if args.command == 'tag':
        if not (args.tag or args.remove):
            raise ValueError('Must specify at least one tag to add or remove')
        for file in args.file:
            note = Notefile(file,**noteopts)
            note.read()
            
            note.modify_tags(add=args.tag,remove=args.remove)
            if not args.no_refresh:
                note.repair_metadata(force=args.force_refresh)
            note.write()
               
    if args.command == 'repair':
        t = '(DRYRUN) ' if args.dry_run else ''
        if args.type in ['both','metadata']:
            for res in repair_metadata(dry_run=args.dry_run,
                                       force=args.force_refresh,
                                       noteopts=noteopts,
                                       **findopts):
                print("{}Updated Metadata '{}'".format(t,res))
        
        if args.type in ['both','orphaned']:
            for old,new,_ in repair_orphaned(dry_run=args.dry_run,
                                             search_path=args.search_path,
                                             search_maxdepth=args.maxdepth,
                                             noteopts=noteopts,
                                             check_mtime=args.mtime,
                                             **findopts):
                print("{}Moved '{}' --> '{}'".format(t,old,new))
    
    if args.command == 'copy':
        copy_note(args.SRC,args.DST,noteopts=noteopts)
         
    if args.command == 'vis':
        t = '(DRYRUN) ' if args.dry_run else ''
        for path in args.path:
            newfindopts = findopts.copy()
            newfindopts['path'] = path
            for note in change_visibility(args.mode,dry_run=args.dry_run,**newfindopts):            
                print("{}Set '{}' to {}".format(t,note,args.mode))
            
    ## Query Actions
    args.out_file = getattr(args,'out_file',None) # Make sure it's set
    stream = sys.stdout if args.out_file is None else open(args.out_file,'wt') 
    
    if args.command == 'change-tag': # THis queries and changes
        t = '(DRYRUN) ' if args.dry_run else ''
        for note in change_tag(args.old_tag,args.new_tag,
                               noteopts=noteopts, # hashfile,link
                               include_orphaned=False,
                               dry_run=args.dry_run,
                               **findopts # path,excludes,matchcase,maxdepth,exclude_links
                               ):
            if not args.no_refresh:
                note.repair_metadata(force=args.force_refresh)
            if not args.silent:
                print('{}Modifed {}'.format(t,note.filename0),file=stream)    
                               

    
    if args.command == 'cat': 
        note = Notefile(args.file,**noteopts)
        note.read()
        print(note.cat(tags=args.tags,full=args.full),file=stream)
            
    if args.command == 'grep':
        end = b'\x00' if args.print0 else b'\n'
        for note in grep(expr=args.expr,
                         expr_matchcase=args.match_expr_case,
                         include_orphaned=False,
                         full_note=args.full,
                         match_any=args.match_any,
                         fixed_strings=args.fixed_strings,
                         full_word=args.full_word,
                         symlink_result=args.symlink,
                         **findopts):
            # python2 will not have a buffer but can accept bytes regardless of mode
            if hasattr(stream,'buffer'):
                stream.buffer.write(note.encode('utf8') + end)
            else: # Will deprecate when not using python2
                stream.write(note.encode('utf8') + end)
    
    if args.command == 'query':
        end = b'\x00' if args.print0 else b'\n'
        for note in query(expr=args.expr,
                          expr_matchcase=args.match_expr_case,
                          include_orphaned=False,
                          fixed_strings=args.fixed_strings,
                          full_word=args.full_word,
                          symlink_result=args.symlink,
                          **findopts):
            # python2 will not have a buffer but can accept bytes regardless of mode
            if hasattr(stream,'buffer'):
                stream.buffer.write(note.encode('utf8') + end)
            else: # Will deprecate when not using python2
                stream.write(note.encode('utf8') + end)
                

    if args.command == 'find':
        end = b'\x00' if args.print0 else b'\n'
        notes = []
        for note in find_notes(include_orphaned=False,
                               return_note=True,
                               noteopts=None,
                               **findopts):
            # python2 will not have a buffer but can accept bytes regardless of mode
            if hasattr(stream,'buffer'):
                stream.buffer.write(note.filename0.encode('utf8') + end)
            else: # Will deprecate when not using python2
                stream.write(note.filename0.encode('utf8') + end)
            
            notes.append(note)
        
        if args.symlink:
            for note in notes:
                symlink_file(note.filename0,args.symlink)  
            
    if args.command == 'search-tags':
        res = search_tags(tags=args.tags,
                          include_orphaned=False,
                          match_any=args.match_any,
                          symlink_result=args.symlink,
                          **findopts)
        if args.tag_only:
            res = list(res.keys())
        yaml.dump(res,stream)
        
    if args.command == 'export':
        res = export(include_orphaned=False,**findopts)
        yaml.dump(res,stream)
        
    # cleanup
    stream.flush()
    if args.out_file is not None:
        stream.close()

if __name__ == '__main__':
    cli()
