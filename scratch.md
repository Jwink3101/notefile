Tests:

Because so much follows the same code paths, I am less worried about testing each and every exclusion and searching.

Some things to test

- X JSON and YAML modes
- X exclusions in general
- X repair exclusions
- X do not repair when cannot uniquely identify
- X filenames with spaces
- X Hidden files
- X symlink output
- X links
    - X Relative links
    - X absolute links
    - X Broken links
    - X Above but from a subdir
    - X Above but to a subdir
    - X Broken because link changed vis
    
New Test List

- X cat
- X tag display
- X symlink in tag mode
- X repair missing hash
- X interactive edit
- X Non-string notes. Modify, grep, replace, and append
- X --note-field


Tasks:

- X setup.py
- X documentation