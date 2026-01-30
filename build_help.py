#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess

os.chdir(os.path.dirname(__file__))

commands = """\
mod
edit
copy
replace
change-tag
vis
show
hide
format
repair
repair-metadata
repair-orphaned
cat
find
export
search
grep
query
tags
note-path"""

commands = [l.strip() for l in commands.split("\n") if l.strip()]
commands.insert(0, None)

helpmd = [
    "# CLI Help",
    (
        "Not all alias commands are listed "
        "(e.g., `grep` is an alias for `search --grep` and isn't included). "
        "`query` is still included for the additional help. "
        "`v1` is also excluded"
    ),
]

for command in commands:
    name = command if command else "No Command"
    helpmd.append(f"# {name}")

    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.argv[0] = 'notefile'; from notefile.cli import cli; cli()",
    ]
    if command:
        cmd.append(command)
    cmd.append("--help")

    help_text = subprocess.check_output(cmd).decode()
    help_text = help_text.replace("usage: cli.py", "usage: notefile")

    helpmd.append(
        f"""
```text
{help_text}
```"""
    )

with open("CLI_help.md", "wt") as f:
    f.write("\n\n".join(helpmd))
