#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for notefile.

Tests are run as if from the CLI but run in Python for the sake of test coverage
"""
from __future__ import division, print_function, unicode_literals

import os
import sys
import shutil
import shlex
import hashlib
import glob
import itertools
import time

import notefile # this *should* import the local version even if it is installed
print('version',notefile.__version__)
print('path',notefile.__file__) # This is just to see that it imported the right now
notefile.DEBUG = False

import ruamel.yaml
yaml = ruamel.yaml.YAML()

import pytest

TESTDIR = os.path.abspath('testdirs')

def call(s):
    if sys.version_info[0] == 2:
        cmd =  shlex.split(s.encode('utf8'))
    else:
        cmd = shlex.split(s)
    return notefile.cli(cmd)

def cleanmkdir(dirpath):
    notefile.DEBUG = False # Reset this
    try:
        shutil.rmtree(dirpath)
    except:
        pass
    os.makedirs(dirpath)

cleanmkdir(TESTDIR)
os.chdir(TESTDIR)

def read_note(filepath,**kwargs):
    note = notefile.Notefile(filepath,**kwargs)
    note.read()
    return note.data

def ishidden(filename,check_dupe=True):
    """
    returns whether a file exists and is hidden.
    Will assert that (a) the file exists and (b) there
    aren't a hidden and visible if check_dupe
    """
    _,vis,hid = notefile.get_filenames(filename)
    if check_dupe and os.path.exists(vis) and os.path.exists(hid):
        assert False, "Duplicate hidden and visible"

    check_vis = os.path.exists(vis) or os.path.islink(vis) # broken links still are fine
    check_hid = os.path.exists(hid) or os.path.islink(hid) # broken links still are fine
    if not (check_hid or check_vis):
        assert False, "Neither file exists"

    return check_hid

##########################

def test_main_note():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'main')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('main.txt','wt') as file:
        file.write('this is a\ntest file')
    
    ## Add
    call('--debug add main.txt "this is a note"')
    data = read_note('main.txt')
    assert "this is a note" == data['notes'].strip()

    call('add main.txt "this is a note"')
    data = read_note('main.txt')
    assert "this is a note\nthis is a note" == data['notes'].strip()

    call('add -r main.txt "this is a note"')
    data = read_note('main.txt')
    assert "this is a note" == data['notes'].strip()
    
    ## Tags
    call('tag -t test -t "two words" main.txt')
    data = read_note('main.txt')
    assert {'test',"two words"} == set(data['tags'])

    call('tag -r "two words" -r "another" main.txt')
    data = read_note('main.txt')
    assert {'test'} == set(data['tags'])
    
    call('tag -r test -t new main.txt') # Add and remove at the same call
    data = read_note('main.txt')
    assert {'new'} == set(data['tags'])
    
    # Test that when the note is unchanged
    
    with open('new.txt','wt') as file:
        file.write('NEW file')
    
    call('add new.txt ""') # Shouldn't change it
    assert not os.path.exists('new.txt.notes.yaml'),'should not have written a note'
    
    call('tag -t atag new.txt')
    hash0 = hashlib.sha1(open('new.txt.notes.yaml','rb').read()).digest()
    
    time.sleep(1.1) # Make sure the 'last-updated' would be modified
    call('tag -t atag new.txt')
    hash1 = hashlib.sha1(open('new.txt.notes.yaml','rb').read()).digest()
    assert hash0 == hash1,'should *not* have written a new note'
    
    call('tag -r atag new.txt')
    call('tag -t atag new.txt')
    hash2 = hashlib.sha1(open('new.txt.notes.yaml','rb').read()).digest()
    assert hash2 != hash0,'The mod date *should* have changed'

    os.chdir(TESTDIR)
    
def test_odd_filenames():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'oddnames')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
  
    filenames = ['spac es.txt','unic·de.txt','unic°de and spaces and no ext','sub dir/dir2/dir 3/hi']
    for filename in filenames:
        dirname = os.path.dirname(filename)
        try:
            os.makedirs(dirname)
        except OSError:
            pass
            
        with open(filename,'wt') as file:
            file.write('this is a\ntest file')
        call('add "{}" "this is a note"'.format(filename))
        call('tag -t mytag "{}" '.format(filename))
        data = read_note(filename)
        assert "this is a note" == data['notes'].strip()
    
    
    # Test --print0. Need to test stdout (especially in python2) and file output
    filenames = set(filenames)
    
    # Just to test stdout to make sure it doesn't throw errors
    call('find')
    call('find -0')
    call('grep "this" ')
    call('grep -0 "this" ')
    call('search-tags') # This outputs YAML so no -0

    # Capture to test
    gold = {'./spac es.txt', './unic°de and spaces and no ext', './unic·de.txt', './sub dir/dir2/dir 3/hi'}
    
    for cmd,nul in itertools.product(['find','grep "this"'],[True,False]):
        if nul:
            cmd += ' -0'
        cmd += ' -o out'
        call(cmd)
        with open('out','rb') as file:
            dat = file.read()
    
        dat = dat.replace(b'\n',b'\x00')
        res = set(d.decode('utf8') for d in dat.split(b'\x00'))
        res = set(r for r in res if r)

        assert res == gold
    
    call('search-tags -o out')
    with open('out') as file:
        d = yaml.load(file)
        res = set(d['mytag'])
    assert res == gold

    os.chdir(TESTDIR)
    
@pytest.mark.parametrize("repair_type", ['both','orphaned','metadata'])
def test_repairs(repair_type):
    """
    Test repairs for the different repair types
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'repairs')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    # Test files
    with open('repair_meta.txt','wt') as file:
        file.write('repair metadata')
    with open('repair_meta_mtime.txt','wt') as file:
        file.write('repair metadata from changing mtime')
    
    with open('repair_orphaned.txt','wt') as file:
        file.write('repair orphaned')
    with open('repair_orphanedDUPE.txt','wt') as file:
        file.write('repair orphanedDUPE')
    
    # Initial Data    
    call('add repair_meta.txt "Metadata repair please"')
    meta0 = read_note('repair_meta.txt')

    call('tag -t mtime repair_meta_mtime.txt')
    meta0_mtime = read_note('repair_meta_mtime.txt')

    call('add repair_orphaned.txt "orphaned repair please"')

    call('add repair_orphanedDUPE.txt "orphaned repair please DUPE"')

    # Break them
    with open('repair_meta.txt','at') as file:
        file.write('\nrepair metadata NOW')
    
    s = os.stat('repair_meta_mtime.txt')
    os.utime('repair_meta_mtime.txt',(s.st_atime - 100,s.st_mtime - 100))
    
    shutil.move('repair_orphaned.txt','repair_orphaned_moved.txt')
    shutil.copy2('repair_orphanedDUPE.txt','repair_orphanedDUPE1.txt')
    shutil.move('repair_orphanedDUPE.txt','repair_orphanedDUPE2.txt')
    
    # Repair the whole directory
    call('repair --type {} .'.format(repair_type))
    
    meta1 = read_note('repair_meta.txt')
    meta1_mtime = read_note('repair_meta_mtime.txt')
    
    if repair_type in ['both','metadata']:
        assert meta1['sha256'] != meta0['sha256']
        assert abs(meta0_mtime['mtime'] - meta1_mtime['mtime'] - 100) < 0.1,'mtime not updated'
    else:
        assert meta1['sha256'] == meta0['sha256'] # Make sure it hasn't changed
        
    if repair_type in ['both','orphaned']:
        assert os.path.exists('repair_orphaned_moved.txt.notes.yaml'),'not found'
        assert not os.path.exists('repair_orphaned.txt.notes.yaml')
              
    else:
        assert not os.path.exists('repair_orphaned_moved.txt.notes.yaml')
        assert os.path.exists('repair_orphaned.txt.notes.yaml')
    # Should *not* have been fixed either way
    assert os.path.exists('repair_orphanedDUPE.txt.notes.yaml') 

    ## Test the --mtime flag if repairing orphaned and for overwrite
    if repair_type in ['both','orphaned']:
        
        with open('orphaned1.txt','wt') as file:file.write('1')
        with open('orphaned2.txt','wt') as file:file.write('2')
        
        call('add orphaned1.txt ONE')
        call('add orphaned2.txt TWO')
        
        shutil.move('orphaned1.txt','Morphaned1.txt')
        shutil.move('orphaned2.txt','Morphaned2.txt')
        
        # Change mtime
        os.utime('Morphaned1.txt',(100,100))
        os.utime('Morphaned2.txt',(100,100))
        
        call('repair --type {} orphaned1.txt.notes.yaml'.format(repair_type))
        call('repair --mtime --type {} orphaned2.txt.notes.yaml'.format(repair_type))
        
        # 1 was moved
        assert os.path.exists('Morphaned1.txt.notes.yaml')
        assert not os.path.exists('orphaned1.txt.notes.yaml')

        # 2 was NOT moved
        assert not os.path.exists('Morphaned2.txt.notes.yaml')
        assert os.path.exists('orphaned2.txt.notes.yaml')
    
        ## Test for overwrite
        with open('orphaned3.txt','wt') as file:file.write('3')
        call('add orphaned3.txt Three')
        shutil.move('orphaned3.txt','Morphaned3.txt')
     
        call('add Morphaned3.txt ThreeV2')
     
        call('repair --type {} orphaned3.txt.notes.yaml'.format(repair_type))
        
        assert os.path.exists('orphaned3.txt.notes.yaml'),'Should NOT have been moved'
        
        call('cat -o out Morphaned3.txt')
        with open('out','rt') as f: note = f.read()
        assert note.strip() ==  'ThreeV2','Should NOT have been changed'

    os.chdir(TESTDIR)

def test_repairs_searchpath():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'repairs-search','deeper')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('file.txt','wt') as file:
        file.write('New File')
    
    call('tag file.txt -t new')
    
    shutil.move('file.txt','../filemoved.txt')
    
    # Should not work
    call('repair')
    assert os.path.exists('file.txt.notes.yaml')

    # Should work
    call('repair --search-path ../')
    assert not os.path.exists('file.txt.notes.yaml')
    assert os.path.exists('../filemoved.txt.notes.yaml')
    
    
    os.chdir(TESTDIR)

def test_repair_dryrun():
    """
    Test that dry-run doesn't do anything
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'repairs_dry')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    
    with open('file.txt','wt') as file: file.write('New File')
    call('add file.txt "testing a note"')
    
    call('cat -f -o out file.txt')
    with open('out') as f: gold = f.read()
    
    # Make it need a metadata repair
    with open('file.txt','at') as file: file.write('Updated File')
    
    call('repair --dry-run -t metadata file.txt ')
    call('cat -f -o out file.txt')
    with open('out') as f: assert f.read() == gold

    call('repair -t metadata file.txt ')
    call('cat -f -o out file.txt')
    with open('out') as f: assert f.read() != gold
    
    
    os.chdir(TESTDIR)
    
    

@pytest.mark.parametrize("link", ['both','symlink','source'])
def test_links(link):
    """
    Test different settings with symlinks
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'links')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
   
    with open('file.txt','wt') as file:
        file.write('Main File')
    
    os.symlink('file.txt','link.txt')
    
    # Need to test multiple commands that modify the note
    
    call('add --link {} link.txt "link note"'.format(link))
    
    call('tag --link {} link.txt -t "link"'.format(link))

    call('add file.txt "file note"')
    call('tag file.txt -t file')
    
    if link == 'both':
        assert os.path.exists('file.txt.notes.yaml')
        assert os.path.exists('link.txt.notes.yaml')
        assert os.path.islink('link.txt.notes.yaml')
        
        # make sure they are the same
        assert hashlib.sha1(open('file.txt.notes.yaml','rb').read()).digest() == \
               hashlib.sha1(open('link.txt.notes.yaml','rb').read()).digest()
    if link == 'source':
        assert os.path.exists('file.txt.notes.yaml')
        assert not os.path.exists('link.txt.notes.yaml')
    
    if link == 'symlink':
        assert os.path.exists('file.txt.notes.yaml')
        assert os.path.exists('link.txt.notes.yaml')
        assert not os.path.islink('link.txt.notes.yaml')
    
        # Make sure they are different
        assert hashlib.sha1(open('file.txt.notes.yaml','rb').read()).digest() != \
               hashlib.sha1(open('link.txt.notes.yaml','rb').read()).digest()

    # Test repair on broken links. The notefile itself should still be
    # okay
    call('add link.txt "new note" --link {}'.format(link))
    shutil.move('file.txt','moved.txt')
    call('repair')

    # Should repair file.txt.notes.yaml but should NOT repair the symlinked note
    assert os.path.exists('moved.txt.notes.yaml') # Repaired
    # NOT moved even if broken. exists required non-broken link so use islink too
    if link != 'source':
        assert os.path.exists('link.txt.notes.yaml') or os.path.islink('link.txt.notes.yaml') 
    

    os.chdir(TESTDIR)

@pytest.mark.parametrize("link", ['both','symlink','source'])
def test_link_overwrite(link):
    """
    Test for writing notes on links, etc. Also tests for using relative
    paths
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'link_overwrite')
    cleanmkdir(dirpath)
    os.chdir(dirpath) 
    #notefile.DEBUG = True  
    
    with open('file.txt','wt') as file:
        file.write('Main File')
    os.makedirs('sub')
    
    os.symlink('../file.txt','sub/link.txt')
    
    call('add --link {} file.txt "file note"'.format(link))
    call('add --link {} sub/link.txt "link note"'.format(link))
    
    gold = 'file note\nlink note'
    try:
        filetxt = read_note('file.txt',link=link)['notes'].strip()
    except:
        filetxt = ''
    
    try:
        linktxt = read_note('sub/link.txt',link=link)['notes'].strip()
    except:
        linktxt = ''
    
    # The `test_links` makes sure this all works. *just* test for overwrite
    if link in ['both','source']: # source will read the source note
        assert filetxt == linktxt == gold
    
    if link == 'source':
        assert not os.path.exists('sub/link.txt.notes.yaml')
        
    if link == 'symlink':
        assert filetxt == 'file note'
        assert linktxt == 'link note'
    
    os.chdir(TESTDIR)
    
def test_excludes_repair():
    """
    Test exclusions in repair, etc
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'excl_repair','noenter')
    cleanmkdir(dirpath)
    os.chdir(dirpath + '/..')
    

    with open('file1.txt','wt') as file:
        file.write('FILE 1')
        
    with open('file2.txt','wt') as file:
        file.write('FILE 2')

    with open('noenter/file3.txt','wt') as file:
        file.write('FILE 3')

    call('add file1.txt "file note1"')

    call('add file2.txt "file note2"')

    call('add noenter/file3.txt "file note3"')
    
    shutil.move('file1.txt','noenter/moved_file1.txt')
    call('repair')
    
    assert os.path.exists('noenter/moved_file1.txt.notes.yaml')
    assert not os.path.exists('file1.txt.notes.yaml')
    
    
    # Test that both the grep for the missing base file (2) respects excludes
    # and that the grep for orphaned files (3) respects it too.
    shutil.move('file2.txt','noenter/moved_file2.txt')
    shutil.move('noenter/file3.txt','moved_file3.txt')
    call('repair --exclude noEnter') # Case shouldn't matter unless set
    
    assert not os.path.exists('noenter/moved_file2.txt.notes.yaml')
    assert os.path.exists('file2.txt.notes.yaml')
    
    assert os.path.exists('noenter/file3.txt.notes.yaml')
    assert not os.path.exists('moved_file3.txt.notes.yaml')
    
    os.chdir(TESTDIR)

def test_maxdepth():
    """
    Test the use of the --maxdepth flag
    in ['repair','grep','list_tags','export']
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'maxdepth')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    depths = ['', 'A', 'B', 'C', 'D']
    
    cleanmkdir('/'.join(depths[1:]))
    
    filepaths = []
    notepaths = []
    
    for id,_ in enumerate(depths):
        p = '/'.join(depths[1:(id+1)])
        name = 'file' + ''.join(depths[1:(id+1)]) + '.txt'
        filepath = os.path.join(p,name)
        with open(filepath,'wt') as file:
            file.write(filepath)
        call('add {} "a note on {}"'.format(filepath,name))
        call('tag {} -t "{}"'.format(filepath,name))
        
        # Damage the note
        notepath = notefile.get_filenames(filepath)[1]
        a,b = os.path.split(notepath)
        shutil.move(notepath,os.path.join(a,'BLA' + b))
        
        filepaths.append('./' + filepath)
        notepaths.append(notepath)

    # Do repairs first
    for depth,_ in enumerate(depths):
        call('repair --max-depth {}'.format(depth))

        # make sure *only* notepaths[:(depth+1)] exist
        # and the rest do not!
        for note in notepaths[:(depth+1)]:
            assert os.path.exists(note)
        for note in notepaths[(depth+1):]:
            assert not os.path.exists(note)
    
    # The rest
    for depth,_ in enumerate(depths):
        gold = set(filepaths[:(depth+1)])
    
        # grep
        call('grep -o out --max-depth {} -- ""'.format(depth))
        with open('out') as file:
            res = set(f.strip() for f in file.read().splitlines() if f.strip())
        assert res == gold

        # search-tags
        call('search-tags -o out --max-depth {}'.format(depth))
        with open('out') as file:
            _res = yaml.load(file)
            res = set()
            for v in _res.values():
                res.update(v)
        assert res == gold

        # export
        call('export -o out --max-depth {}'.format(depth))
        with open('out') as file:
            _res = yaml.load(file)
            res = set(_res['notes'])  
        assert res == gold
    
    os.chdir(TESTDIR)

def test_grep_and_listtags_and_export_and_find():
    """
    Tests greping including for tags
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'grep','noenter')
    cleanmkdir(dirpath)
    os.chdir(dirpath + '/..')
    
    with open('file1.txt','wt') as file:
        file.write('FILE 1')
        
    with open('file2.txt','wt') as file:
        file.write('FILE 2')

    with open('noenter/file3.txt','wt') as file:
        file.write('FILE 3')  
        
    with open('file4.exc','wt') as file:
        file.write('FILE 4')

    with open('file5.txt','wt') as file:
        file.write('FILE 5')


    call('add file1.txt "note for myfile 1"')
    call('tag file1.txt -t tag1 -t tag2')

    call('add file2.txt "note\nfor MyFiLe 2"')

    call('add noenter/file3.txt "myfile 3 but do not find me"')
    call('tag noenter/file3.txt -t tag1')

    call('add file4.exc "myfile 4 but do not find me either"')
    call('tag file4.exc -t tag1')
    
    call('add file5.txt "yourfile 5"')
  
    ## Greps
    
    call('grep -o out MyFiLe')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt', './file1.txt', './file4.exc', './file2.txt'} == res

    call('grep -o out MyFiLe --match-expr-case')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file2.txt'} == res
    
    call('grep -o out MyFiLe --exclude "*.exc" --exclude noEnter')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file1.txt','./file2.txt'} == res

    call('grep -o out MyFiLe --exclude "*.exc" --exclude noEnter --match-exclude-case')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt','./file1.txt','./file2.txt'} == res
    
    call('grep -o out MyFiLe YouRFile')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt', './file1.txt', './file4.exc', './file2.txt','./file5.txt'} == res
    
    # Test grep with full
    nf = notefile.Notefile('file1.txt')
    nf.read()
    nf.data['new_field'] = "this is a special field"
    nf.write()
    
    call('grep special -o out')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert len(res) == 0
    
    call('grep special -f -o out')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert res == {'./file1.txt'}
    
    ### Tags
    
    call('search-tags -o out')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}, 'tag2': {'./file1.txt'}} == res
    

    call('search-tags -o out tag1')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}} == res
    
    call('search-tags -o out tag1 --exclude "*.EXC" --match-exclude-case')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file4.exc','./file1.txt'}} == res   

    call('search-tags -o out tag1 --exclude "*.EXC"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file1.txt'}} == res   
    
    ## Fancy Queries
    call('search-tags -o out "tag1" "tag2"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./file1.txt', './file4.exc', './noenter/file3.txt'}, 
            'tag2': {'./file1.txt'}} == res
    
    call('search-tags -o out --all "tag1" "tag2"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./file1.txt'}, 'tag2': {'./file1.txt'}} == res
    
    ## --filters. Also use a mix of caps to test that it gets fixed
    call("""search-tags -o out --filter "'tag1' in tags and 'tAG2' not in tags" """)
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert res == {"'tag1' in tags and 'tag2' not in tags":  # made lowercase
                      {'./file4.exc', './noenter/file3.txt'}} # NOT ./file1.txt
    # Multiple
    call("""search-tags -o out --filter "'tag1' in tags and 'tAG2' not in tags" '"tag2" in tags' """)
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert res == {"'tag1' in tags and 'tag2' not in tags": 
                        {'./file4.exc', './noenter/file3.txt'}, 
                   '"tag2" in tags':  # Different quote pattern to match the query
                        {'./file1.txt'}}

    # Multiple --all
    call("""search-tags -o out --all --filter "'tag1' in tags and 'tAG2' not in tags" '"tag2" in tags' """)
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert res == {}

    
    ## Link Excludes
    # Add this after the previous
    with open('file6.txt','wt') as file:
        file.write('FILE 6')
    os.symlink('file6.txt','link.txt')
    
    call('add --link both link.txt "this is a link"')
    call('tag --link both link.txt -t link')
    call('tag file6.txt -t tag1')
    call('tag file1.txt -t no_link')
    
    call('grep -o out link')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./link.txt', './file6.txt'} == res
    
    call('grep -o out link --exclude-links')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file6.txt'} == res

    call('search-tags -o out link')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./link.txt', './file6.txt'}} == res

    call('search-tags -o out link --exclude-links')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./file6.txt'}} == res
    
    ## Export & find. Mostly test for exclusions
    def _read(filename,export=True):
        if export:
            with open(filename) as file:
                res = yaml.load(file)
                # Just look at the files
                return set(res['notes'].keys())
        with open(filename) as file:
            return set(l.strip() for l in file.readlines() if l.strip())
            
    for cmd in ['export','find']:
        call('{} -o out'.format(cmd))
        res = _read('out',export=cmd=='export')
        assert {'./file6.txt', './file5.txt', './link.txt', 
                './noenter/file3.txt', './file2.txt', './file4.exc', 
                './file1.txt'} == res

        call('{} -o out --exclude-links'.format(cmd))
        res = _read('out',export=cmd=='export')
        assert {'./file6.txt', './file5.txt',
                './noenter/file3.txt', './file2.txt', './file4.exc', 
                './file1.txt'} == res

        call('{} -o out --exclude "*.exC"'.format(cmd))
        res = _read('out',export=cmd=='export')
        assert {'./file6.txt', './file5.txt', './link.txt', 
                './noenter/file3.txt', './file2.txt', 
                './file1.txt'} == res

        call('{} -o out --exclude "*.exC" --match-exclude-case'.format(cmd))
        res = _read('out',export=cmd=='export')
        assert {'./file6.txt', './file5.txt', './link.txt', 
                './noenter/file3.txt', './file2.txt', './file4.exc', 
                './file1.txt'} == res
    
    os.chdir(TESTDIR)

def test_grep_w_multiple_expr():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'multi-grep')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('file1.txt','wt') as file:
        file.write('FILE 1')
        
    with open('file2.txt','wt') as file:
        file.write('FILE 2')
    
    with open('file3.txt','wt') as file:
        file.write('FILE 3')


    call('add file1.txt "match me or you"')
    call('add file2.txt "match you"')
    call('add file3.txt "what about me"')
    
    # tests
    call('grep -o out me you')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file1.txt', './file2.txt', './file3.txt'} == res

    call('grep -o out --all me you')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file1.txt'} == res
    
    
    ## Test grep with regex
    with open('file4.txt','wt') as file:file.write('FILE 4')
    with open('file5.txt','wt') as file:file.write('FILE 5')
    with open('file6.txt','wt') as file:file.write('FILE 6')
    with open('file7.txt','wt') as file:file.write('FILE 7')
    
    call('add file4.txt "this is a te.*st"')
    call('add file5.txt "This is a teblablabast"')
    call('add file6.txt "These are their words"')
    call('add file7.txt "these are the words"')
    
    call('grep -o out "te.*st"') 
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file4.txt','./file5.txt'} == res
    
    call('grep -o out -F "te.*st"')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file4.txt'} == res
        
    call('grep -o out the')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file6.txt','./file7.txt'} == res

    call('grep -o out --full-word the')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file7.txt'} == res
    
    
    os.chdir(TESTDIR)

def test_nohash():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'nohash')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    nohash = lambda filename: read_note(filename,hashfile=False).get('sha256',notefile.NOHASH) == notefile.NOHASH
    
    with open('file1.txt','wt') as file:
        file.write('FILE 1')
        
    with open('file2.txt','wt') as file:
        file.write('FILE 2')
    
    with open('file3.txt','wt') as file:
        file.write('FILE 3')
    
    with open('file4.txt','wt') as file:
        file.write('FILE 4')

    with open('file5.txt','wt') as file:
        file.write('FILE 5')
    
    
    # make sure no hash is computed when read with nothing
    assert nohash('file1.txt') 
    assert nohash('file2.txt') 
    
    call('add file1.txt "testing" --no-hash') # Add note when none existed
    assert nohash('file1.txt') 
    
    call('tag file2.txt file1.txt -t hi --no-hash') # Add tag to new and existing
    assert nohash('file2.txt') 
    
    call('add file1.txt "append" --no-hash') # Add note to existing
    assert nohash('file1.txt')
    
    ## NOTE: edit has to be tested manually! See bottom
    
    # Test that repair adds a hash as needed
    
    with open('file1.txt','at') as file:
        file.write('FILE 1')
        
    with open('file2.txt','at') as file:
        file.write('FILE 2')
        
    call('repair file1.txt')
    assert not nohash('file1.txt') # SHOULD have a hash
    
    call('repair file2.txt --no-hash')
    assert nohash('file2.txt') # still no hash
    
    # Test that we *can* repair file1.txt since it now has a hash but we cannot
    # repair file2
    shutil.move('file1.txt','fileA.txt')
    shutil.move('file2.txt','fileB.txt')
    
    call('repair')
    
    ## Test edits and repairs with and without --no-hash or --
    
    # Add again to a no-hashed file
    call('add --no-hash file3.txt Comment 1')
    call('add file3.txt Comment 2') # Notice no --no-hash
    assert nohash('file3.txt')
    
    # Modify the file and then add again with --nohash
    with open('file3.txt','at') as file: file.write('new line')
    call('add --no-hash file3.txt Comment 3')
    assert nohash('file3.txt')
    
    # Modify the file and then add again withOUT --nohash. Should get hashed
    with open('file3.txt','at') as file: file.write('new line2')
    call('add file3.txt Comment 4')
    assert not nohash('file3.txt')
    
    # Test repairs after --no-hash
    call('add --no-hash file4.txt Comment 1')
    call('repair --type metadata file4.txt') # Will not rehash since unmodified
    assert nohash('file4.txt')
    
    # Edit the file then repair with --no-hash
    with open('file4.txt','at') as file: file.write('new line2')
    call('repair --type metadata --no-hash file4.txt') # Will not rehash since unmodified
    assert nohash('file4.txt')
    
    # Repair again withOUT --no-hash but NON-edited file
    call('repair --type metadata file4.txt') # Will not rehash since unmodified
    assert nohash('file4.txt')
    
    # Edit the file then repair withOUT --no-hash
    with open('file4.txt','at') as file: file.write('new line3')
    call('repair --type metadata  file4.txt') # Will not rehash since unmodified
    assert not nohash('file4.txt')
    
    # Test that repair with --force-refresh WILL rehash missing ones
    call('add --no-hash file5.txt Comment 1')
    call('repair --type metadata --force-refresh --dry-run file5.txt') # Make sure this doesn't add it
    assert nohash('file5.txt')
    call('repair --type metadata --force-refresh file5.txt') # Make sure this doesn't add it
    assert not nohash('file5.txt')
    
    os.chdir(TESTDIR)

@pytest.mark.parametrize("link", ['both','symlink','source'])
def test_hidden(link):
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'hidden')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('file1.txt','wt') as file: file.write('file1')
    with open('file2.txt','wt') as file: file.write('file2')
    with open('file3.txt','wt') as file: file.write('file3')
    
    # test when and when not specified and make sire the mode doesn't change
    call('add --hidden file1.txt "note 1"')
    assert ishidden('file1.txt')
    
    call('add --hidden file1.txt "note 2"')
    assert ishidden('file1.txt')
    
    call('add file1.txt "note 3"') # Doesn't change hide mode
    assert ishidden('file1.txt')
    
    call('tag --hidden -t t1 file1.txt')
    assert ishidden('file1.txt')
    
    call('tag -t t2 file1.txt')
    assert ishidden('file1.txt')
    
    call('tag -t file2 file2.txt --visible')
    assert not ishidden('file2.txt')
    
    # Test linking
    os.symlink('file1.txt','link1.txt')
    os.symlink('file2.txt','link2.txt')
    os.symlink('file3.txt','link3.txt')
    call('tag -t link1 link1.txt --visible --link {}'.format(link)) # make sure it doesn't change visibility
    call('tag -t link2 link2.txt --hidden  --link {}'.format(link))
    
    if link in ['both','symlink']:
        assert os.path.exists('link1.txt.notes.yaml')
        assert os.path.exists('.link2.txt.notes.yaml')
    else:
        assert len(glob.glob('*link*.txt.notes.yaml')) == 0
    
    call('vis show link2.txt')
    call('vis hide link1.txt')
    # Make sure the refferents haven't changed
    assert os.path.exists('.file1.txt.notes.yaml')
    assert os.path.exists('file2.txt.notes.yaml')
    
    if link in ['both','symlink']:
        # The link should have changed
        assert os.path.exists('.link1.txt.notes.yaml')
        assert os.path.exists('link2.txt.notes.yaml')
    else:
        assert len(glob.glob('*link*.txt.notes.yaml')) == 0
    
    
    # Flip the links again to make sure the refferent hasn't changed
    call('vis hide link2.txt')
    call('vis show link1.txt')
    # Make sure the refferents haven't changed
    assert os.path.exists('.file1.txt.notes.yaml')
    assert os.path.exists('file2.txt.notes.yaml')
    if link in ['both','symlink']:
        assert os.path.exists('link1.txt.notes.yaml')
        assert os.path.exists('.link2.txt.notes.yaml')
    else:
        assert len(glob.glob('*link*.txt.notes.yaml')) == 0
    
    # Conflicts on show and hide
    shutil.copy2('file2.txt.notes.yaml','.file2.txt.notes.yaml')
    call('vis hide file2.txt')
    assert os.path.exists('.file2.txt.notes.yaml') # Both still exist
    assert os.path.exists('file2.txt.notes.yaml')
    call('vis show file2.txt')
    assert os.path.exists('.file2.txt.notes.yaml') # Both still exist
    assert os.path.exists('file2.txt.notes.yaml')
    
    # This part tests broken links due to hiding and unhiding
    # From the docs (as of testing):
    #
    # > Changing the visibility of a symlinked referent will cause the 
    # > symlinked note to be broken. However, by design it will still 
    # > properly read the note and will be fixed when editing or repairing 
    # > metadata.
    #
    if link == 'both': # Doesn't apply to the others since they don't symlink the note
        with open('file4.txt','wt') as file: file.write('file4')
        os.symlink('file4.txt','link4.txt')
        call('add --link {} -V link4.txt note'.format(link))
        
        # Make the file4 note hidden
        call('vis hide file4.txt')
        
        assert os.path.islink('link4.txt.notes.yaml') # Still there (visible)
        assert not os.path.exists('link4.txt.notes.yaml') # Broken will be False
        assert not os.path.exists('.link4.txt.notes.yaml') # did not get hidden
        
        # Still can be read
        call('cat -o out link4.txt')
        with open('out','rt') as file:
            assert file.read().strip() == 'note'
        
        # Can still be hidden with OUT repair
        call('vis hide link4.txt')
        assert ishidden('link4.txt')
        
        # Editing should (a) still work, (b) fix it
        # (by design of sorts. See copy of doc)
        call('add --link {} link4.txt notenew'.format(link))
        assert os.path.islink('.link4.txt.notes.yaml') # Still there (hidden)
        assert os.path.exists('.link4.txt.notes.yaml') # No longer broken
        
        # Break it again. Make sure it's broken
        call('vis show file4.txt')
        assert os.path.islink('.link4.txt.notes.yaml') # Still there (hidden)
        assert not os.path.exists('.link4.txt.notes.yaml') # NOW it IS broken
        
        # Make sure dry-run does NOT repair
        call('repair --dry-run --type metadata link4.txt')
        assert os.path.islink('.link4.txt.notes.yaml') # Still there (hidden)
        assert not os.path.exists('.link4.txt.notes.yaml') # No longer broken
        
        # Repair for real        
        call('repair --type metadata link4.txt')
        assert os.path.islink('.link4.txt.notes.yaml') # Still there (hidden)
        assert os.path.exists('.link4.txt.notes.yaml') # No longer broken
        
    
    # Test that the hidden stat is preserved
    with open('repair1.txt','wt') as file: file.write('repair1')
    with open('repair2.txt','wt') as file: file.write('repair2')
    
    call('add -V repair1.txt note1')
    call('add -H repair2.txt note2')
    shutil.move('repair1.txt','repairME1.txt')
    shutil.move('repair2.txt','repairME2.txt')
    call('repair -t orphaned')
    
    assert os.path.exists('repairME1.txt.notes.yaml')
    assert not os.path.exists('.repairME1.txt.notes.yaml')
    
    assert not os.path.exists('repairME2.txt.notes.yaml')
    assert os.path.exists('.repairME2.txt.notes.yaml')
    
    
    
    os.chdir(TESTDIR)

@pytest.mark.parametrize("hide_flag,hash_flag", [('-H', ''), ('-H', '--no-hash'), ('-V', ''), ('-V', '--no-hash')])
def test_copy_flags(hide_flag,hash_flag):
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'copy_flags')
    cleanmkdir(dirpath)
    os.chdir(dirpath)

    with open('file1.txt','wt') as file: file.write('file1')
    with open('file2.txt','wt') as file: file.write('file2')
    
    call('add file1.txt "A Note"')
    call('tag -t mytag file1.txt')
    
    # Add a new non-standard field and make sure that gets copied too
    src = notefile.Notefile('file1.txt').read()
    src.data['arb'] = {'my':'data'}
    src.write()
    
    src_data = read_note('file1.txt')
    
    call('copy {} {} file1.txt file2.txt'.format(hide_flag,hash_flag))
        
    dst_data = read_note('file2.txt')
    for key in ['notes','tags','arb']:
        assert src_data[key] == dst_data[key]
    
    dhash = dst_data.get('sha256','')
    if hash_flag == '--no-hash':
        assert len(dhash) != 64
    else:
        assert len(dhash) == 64 
    
    if hide_flag == '-H':
        assert     os.path.exists('.file2.txt.notes.yaml')
        assert not os.path.exists('file2.txt.notes.yaml')
    else:
        assert not os.path.exists('.file2.txt.notes.yaml')
        assert     os.path.exists('file2.txt.notes.yaml')
    
    # Test that you cannot copy again
    try:
        print('Expect exception or exit depending on debug flag')
        call('copy {} {} file1.txt file2.txt'.format(hide_flag,hash_flag))
        assert False, "expected error"
    except BaseException: # BaseException includes SystemExit
        pass

    os.chdir(TESTDIR)   

@pytest.mark.parametrize("link", ['both','symlink','source'])
def test_copy_with_links(link):
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'copy_link')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('src1.txt','wt') as file: file.write('src1')
    with open('src2.txt','wt') as file: file.write('src2')
    with open('dst1.txt','wt') as file: file.write('dst1')
    with open('dst2.txt','wt') as file: file.write('dst2')
    os.symlink('src1.txt','linksrc.txt')
    os.symlink('dst2.txt','linkdst.txt')
    
    ## SRC is a link
    # Skip for 'source' mode since it is supposed to have its own notefile
    if link in ['both','symlink']:
        call('add --link {} linksrc.txt "my source"'.format(link))
        call('tag --link {} -t mytag linksrc.txt'.format(link))
    
        # Add a new non-standard field and make sure that gets copied too
        src = notefile.Notefile('linksrc.txt',link=link).read()
        src.data['arb'] = {'my':'data'}
        src.write()
        src_data = read_note('linksrc.txt',link=link)

        # --link flag is meaningless since dst isn't a link
        call('copy linksrc.txt dst1.txt')
        dst_data = read_note('dst1.txt')
        for key in ['notes','tags','arb']:
            assert src_data[key] == dst_data[key]
    
    ## DST is a link
    call('add src2.txt "my source2"')
    call('tag -t mytag2 src2.txt')
    
    # Add a new non-standard field and make sure that gets copied too
    src = notefile.Notefile('src2.txt').read()
    src.data['arb'] = {'my':'data'}
    src.write()
    src_data = read_note('src2.txt',link=link)
      
    call('copy --link {} src2.txt linkdst.txt'.format(link))
    dst_data = read_note('linkdst.txt',link=link)
    for key in ['notes','tags','arb']:
        assert src_data[key] == dst_data[key]
    
    if link in ['both','symlink']:
        assert os.path.exists('linkdst.txt.notes.yaml')
    if link in ['both','source']:
        assert os.path.exists('src2.txt.notes.yaml')
    
    if link == 'source':
        assert not os.path.exists('linkdst.txt.notes.yaml')
    
    
    os.chdir(TESTDIR)   


if __name__ == '__main__': 
    test_main_note()
    test_odd_filenames()
    test_repairs('both')
    test_repairs('orphaned')
    test_repairs('metadata')
    test_repairs_searchpath()
    test_repair_dryrun()
    test_links('both')
    test_links('symlink')
    test_links('source')
    test_link_overwrite('both')
    test_link_overwrite('symlink')
    test_link_overwrite('source')
    test_excludes_repair()
    test_grep_and_listtags_and_export_and_find()
    test_grep_w_multiple_expr()
    test_nohash()
    test_maxdepth()
    test_hidden('both')
    test_hidden('symlink')
    test_hidden('source')
    for hide_flag,hash_flag in [('-H', ''), ('-H', '--no-hash'), ('-V', ''), ('-V', '--no-hash')]:
        test_copy_flags(hide_flag,hash_flag)
    test_copy_with_links('both')
    test_copy_with_links('symlink')
    test_copy_with_links('source')
    
    print('ALL TESTS PASS') # In case we do not get to this from a sys.exit()
    pass
    
os.chdir(TESTDIR)
## Manual Testing
# Not everything gets tested automatically but it should be easy enough to test
# manually. The following is a list of key items to test manually
#
# * Adding Notes via stdin: 
#     * `-r`
#     * Default
# Editing notes
#     * regular & --full
#     * Tags in edited notes
#     * link modes (this is a different pathway than `add` but the link-logic
#       goes through the same codes
#     * --no-hash does not set a hash!












