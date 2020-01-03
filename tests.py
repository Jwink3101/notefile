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

import ruamel.yaml
yaml = ruamel.yaml.YAML()

import pytest

TESTDIR = os.path.abspath('testdirs')

def ssplit(s):
    if sys.version_info[0] == 2:
        return shlex.split(s.encode('utf8'))
    return shlex.split(s)

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
    cmd = 'add main.txt "this is a note"'
    notefile.cli(ssplit(cmd))
    _,data = notefile.read_data('main.txt')
    assert "this is a note" == data['notes'].strip()

    cmd = 'add main.txt "this is a note"'
    notefile.cli(ssplit(cmd))
    _,data = notefile.read_data('main.txt')
    assert "this is a note\n\nthis is a note" == data['notes'].strip()

    cmd = 'add -r main.txt "this is a note"'
    notefile.cli(ssplit(cmd))
    _,data = notefile.read_data('main.txt')
    assert "this is a note" == data['notes'].strip()
    
    ## Tags
    cmd = 'tag -t test -t "two words" main.txt'
    notefile.cli(ssplit(cmd))
    
    _,data = notefile.read_data('main.txt')
    assert {'test',"two words"} == set(data['tags'])

    cmd = 'tag -t "two words" -t "another" -r main.txt'
    notefile.cli(ssplit(cmd))
    
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
        cmd = 'add "{}" "this is a note"'.format(filename)
        notefile.cli(ssplit(cmd))
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
    cmd = 'add repair_meta.txt "Metadata repair please"'
    notefile.cli(ssplit(cmd))
    _,meta0 = notefile.read_data('repair_meta.txt')

    cmd = 'add repair_orphaned.txt "orphaned repair please"'
    notefile.cli(ssplit(cmd))

    cmd = 'add repair_orphanedDUPE.txt "orphaned repair please DUPE"'
    notefile.cli(ssplit(cmd))

    # Break them
    with open('repair_meta.txt','at') as file:
        file.write('\nrepair metadata NOW')
    
    shutil.move('repair_orphaned.txt','repair_orphaned_moved.txt')
    shutil.copy('repair_orphanedDUPE.txt','repair_orphanedDUPE1.txt')
    shutil.move('repair_orphanedDUPE.txt','repair_orphanedDUPE2.txt')
    
    # Repair the whole directory
    cmd = 'repair --type {} .'.format(repair_type)
    notefile.cli(ssplit(cmd))
    
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
    
    cmd = '--link {} add link.txt "link note"'.format(link)
    notefile.cli(ssplit(cmd))
    
    cmd = '--link {} tag link.txt -t "link"'.format(link)
    notefile.cli(ssplit(cmd))

    cmd = 'add file.txt "file note"'
    notefile.cli(ssplit(cmd))
    cmd = 'tag file.txt -t file'
    notefile.cli(ssplit(cmd))
    
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

    cmd = 'add file1.txt "file note1"'
    notefile.cli(ssplit(cmd))

    cmd = 'add file2.txt "file note2"'
    notefile.cli(ssplit(cmd))

    cmd = 'add noenter/file3.txt "file note3"'
    notefile.cli(ssplit(cmd))
    
    shutil.move('file1.txt','noenter/moved_file1.txt')
    cmd = 'repair'
    notefile.cli(ssplit(cmd))
    
    assert os.path.exists('noenter/moved_file1.txt.notes.yaml')
    assert not os.path.exists('file1.txt.notes.yaml')
    
    
    # Test that both the search for the missing base file (2) respects excludes
    # and that the search for orphaned files (3) respects it too.
    shutil.move('file2.txt','noenter/moved_file2.txt')
    shutil.move('noenter/file3.txt','moved_file3.txt')
    cmd = 'repair --exclude noEnter' # Case shouldn't matter unless set
    notefile.cli(ssplit(cmd))
    
    assert not os.path.exists('noenter/moved_file2.txt.notes.yaml')
    assert os.path.exists('file2.txt.notes.yaml')
    
    assert os.path.exists('noenter/file3.txt.notes.yaml')
    assert not os.path.exists('moved_file3.txt.notes.yaml')
    
    
    os.chdir(TESTDIR)

def test_search_export():
    """
    Tests searching including for tags
    """
    os.chdir(TESTDIR)
    dirpath = os.path.join(TESTDIR,'search','noenter')
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


    cmd = 'add file1.txt "note for myfile 1"'
    notefile.cli(ssplit(cmd))
    cmd = 'tag file1.txt -t tag1 -t tag2'
    notefile.cli(ssplit(cmd))

    cmd = 'add file2.txt "note\nfor MyFiLe 2"'
    notefile.cli(ssplit(cmd))

    cmd = 'add noenter/file3.txt "myfile 3 but do not find me"'
    notefile.cli(ssplit(cmd))
    cmd = 'tag noenter/file3.txt -t tag1'
    notefile.cli(ssplit(cmd))

    cmd = 'add file4.exc "myfile 4 but do not find me either"'
    notefile.cli(ssplit(cmd))
    cmd = 'tag file4.exc -t tag1'
    notefile.cli(ssplit(cmd))
    
    cmd = 'add file5.txt "yourfile 5"'
    notefile.cli(ssplit(cmd))
  
    ## Searches
    
    cmd = 'search -o out MyFiLe'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt', './file1.txt', './file4.exc', './file2.txt'} == res

    cmd = 'search -o out MyFiLe --match-expr-case'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file2.txt'} == res
    
    cmd = 'search -o out MyFiLe --exclude "*.exc" --exclude noEnter'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file1.txt','./file2.txt'} == res

    cmd = 'search -o out MyFiLe --exclude "*.exc" --exclude noEnter --match-exclude-case'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt','./file1.txt','./file2.txt'} == res
    
    cmd = 'search -o out MyFiLe YouRFile'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./noenter/file3.txt', './file1.txt', './file4.exc', './file2.txt','./file5.txt'} == res
    
    ### Tags
    
    cmd = 'list-tags -o out'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}, 'tag2': {'./file1.txt'}} == res
    

    cmd = 'list-tags -o out tag1'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt', './file4.exc', './file1.txt'}} == res
    
    cmd = 'list-tags -o out tag1 --exclude "*.EXC" --match-exclude-case'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file4.exc','./file1.txt'}} == res   

    cmd = 'list-tags -o out tag1 --exclude "*.EXC"'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'tag1': {'./noenter/file3.txt','./file1.txt'}} == res   
    
    ## Link Excludes
    # Add this after the previous
    with open('file6.txt','wt') as file:
        file.write('FILE 6')
    os.symlink('file6.txt','link.txt')
    
    cmd = '--link both add link.txt "this is a link"'
    notefile.cli(ssplit(cmd))
    cmd = '--link both tag link.txt -t link'
    notefile.cli(ssplit(cmd))
    
    cmd = 'search -o out link'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./link.txt', './file6.txt'} == res
    
    cmd = 'search -o out link --exclude-links'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = set(f.strip() for f in file.read().splitlines() if f.strip())
    assert {'./file6.txt'} == res

    cmd = 'list-tags -o out link'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./link.txt', './file6.txt'}} == res

    cmd = 'list-tags -o out link --exclude-links'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Convert to dict of sets for ordering
        res = {k:set(v) for k,v in res.items()}
    assert {'link': {'./file6.txt'}} == res
    
    ## Export
    cmd = 'export -o out'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res

    cmd = 'export -o out --exclude-links'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt',
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res

    cmd = 'export -o out --exclude "*.exC"'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', 
            './file1.txt'} == res

    cmd = 'export -o out --exclude "*.exC" --match-exclude-case'
    notefile.cli(ssplit(cmd))
    with open('out') as file:
        res = yaml.load(file)
        # Just look at the files
        res = set(res['notes'].keys())
    assert {'./file6.txt', './file5.txt', './link.txt', 
            './noenter/file3.txt', './file2.txt', './file4.exc', 
            './file1.txt'} == res
    
    os.chdir(TESTDIR)
if __name__ == '__main__': 
    test_search_export()
    test_main_note()
    test_repairs('orphaned')
    test_repairs('metadata')
    test_repairs('both')
    test_odd_filenames()
    test_links('symlink')
    test_links('source')
    test_links('both')
    test_excludes_repair()

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
# 












