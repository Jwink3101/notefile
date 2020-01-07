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

import notefile # this *should* import the local version even if it is installed
print('version',notefile.__version__)
print('path',notefile.__file__)
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
    try:
        shutil.rmtree(dirpath)
    except:
        pass
    os.makedirs(dirpath)

cleanmkdir(TESTDIR)
os.chdir(TESTDIR)

def test_main_note():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'main')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    with open('main.txt','wt') as file:
        file.write('this is a\ntest file')
    
    ## Add
    call('add main.txt "this is a note"')
    _,data = notefile.read_data('main.txt')
    assert "this is a note" == data['notes'].strip()

    call('add main.txt "this is a note"')
    _,data = notefile.read_data('main.txt')
    assert "this is a note\n\nthis is a note" == data['notes'].strip()

    call('add -r main.txt "this is a note"')
    _,data = notefile.read_data('main.txt')
    assert "this is a note" == data['notes'].strip()
    
    ## Tags
    call('tag -t test -t "two words" main.txt')
    
    _,data = notefile.read_data('main.txt')
    assert {'test',"two words"} == set(data['tags'])

    call('tag -t "two words" -t "another" -r main.txt')
    
    _,data = notefile.read_data('main.txt')
    assert {'test'} == set(data['tags'])

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
        _,data = notefile.read_data(filename)
        assert "this is a note" == data['notes'].strip()
    
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
    with open('repair_orphaned.txt','wt') as file:
        file.write('repair orphaned')

    with open('repair_orphanedDUPE.txt','wt') as file:
        file.write('repair orphanedDUPE')
    
    # Initial Data    
    call('add repair_meta.txt "Metadata repair please"')
    _,meta0 = notefile.read_data('repair_meta.txt')

    call('add repair_orphaned.txt "orphaned repair please"')

    call('add repair_orphanedDUPE.txt "orphaned repair please DUPE"')

    # Break them
    with open('repair_meta.txt','at') as file:
        file.write('\nrepair metadata NOW')
    
    shutil.move('repair_orphaned.txt','repair_orphaned_moved.txt')
    shutil.copy('repair_orphanedDUPE.txt','repair_orphanedDUPE1.txt')
    shutil.move('repair_orphanedDUPE.txt','repair_orphanedDUPE2.txt')
    
    # Repair the whole directory
    call('repair --type {} .'.format(repair_type))
    
    _,meta1 = notefile.read_data('repair_meta.txt')
    
    if repair_type in ['both','metadata']:
        assert meta1['sha256'] != meta0['sha256']
    else:
        assert meta1['sha256'] == meta0['sha256'] # Make sure it hasn't changed
        
    if repair_type in ['both','orphaned']:
        assert os.path.exists('repair_orphaned_moved.txt.notes.yaml')
        assert not os.path.exists('repair_orphaned.txt.notes.yaml')
              
    else:
        assert not os.path.exists('repair_orphaned_moved.txt.notes.yaml')
        assert os.path.exists('repair_orphaned.txt.notes.yaml')
    
    # Should *not* have been fixed either way
    assert os.path.exists('repair_orphanedDUPE.txt.notes.yaml') 

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

    os.chdir(TESTDIR)


def test_excludes_repair():
    """
    Test exclusions in repair, etx
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

def test_grep_export():
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
    _,data = notefile.read_data('file1.txt')
    data['new_field'] = "this is a special field"
    notefile.write_data('file1.txt',data)

    call('grep special -o out')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert len(res) == 0
    
    call('grep special -f -o out')
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert res == {'./file1.txt'}
    
    ### Tags
    
    call('list-tags -o out')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}, 'tag2': {'./file1.txt'}} == res
    

    call('list-tags -o out tag1')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}} == res
    
    call('list-tags -o out tag1 --exclude "*.EXC" --match-exclude-case')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file4.exc','./file1.txt'}} == res   

    call('list-tags -o out tag1 --exclude "*.EXC"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file1.txt'}} == res   
    
    ## Fancy Queries
    call('list-tags -o out "tag1 or tag2"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1 or tag2': {'./noenter/file3.txt', './file1.txt', './file4.exc'}} == res
    
    call('list-tags -o out "tag1 and not tag2"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1 and not tag2': {'./noenter/file3.txt', './file4.exc'}} == res
    
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

    call('list-tags -o out link')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./link.txt', './file6.txt'}} == res

    call('list-tags -o out link --exclude-links')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./file6.txt'}} == res

    # One more complex query
    call('list-tags -o out "(tag1 or link) and not no_link"')
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'(tag1 or link) and not no_link': {'./noenter/file3.txt', './link.txt', './file4.exc', './file6.txt'}} == res
    
    ## Export
    call('export -o out')
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res

    call('export -o out --exclude-links')
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt',
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res

    call('export -o out --exclude "*.exC"')
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', 
            './file1.txt'} == res

    call('export -o out --exclude "*.exC" --match-exclude-case')
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res
    
    os.chdir(TESTDIR)
    

def test_nohash():
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'nohash')
    cleanmkdir(dirpath)
    os.chdir(dirpath)
    
    nohash = lambda filename: notefile.read_data(filename)[1]['sha256'] == notefile.NOHASH
    
    with open('file1.txt','wt') as file:
        file.write('FILE 1')
        
    with open('file2.txt','wt') as file:
        file.write('FILE 2')
    
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
    
    
    
    
    os.chdir(TESTDIR)
if __name__ == '__main__': 
    test_main_note()
    test_odd_filenames()
    test_repairs(both)
    test_repairs(orphaned)
    test_repairs(metadata)
    test_repairs_searchpath()
    test_links(both)
    test_links(symlink)
    test_links(source)
    test_excludes_repair()
    test_grep_export()
    test_nohash()

## Manual Testing
# Not everything gets tested automatically but it should be easy enough to test
# manually. The following is a list of key items to test manually
#
# * Adding Notes via stdin: 
#     * `-r`
#     * Default
# Editing notes
#     * regular
#     * link modes (this is a different pathway than `add` but the link-logic
#       goes through the same codes
#     * --no-hash does not set a hash!












