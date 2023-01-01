#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import subprocess

os.chdir(os.path.dirname(__file__))

commands = """\
mod
copy
replace
change-tag
vis
format
repair
cat
find
search
query
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

    cmd = [sys.executable, "notefile.py"]
    if command:
        cmd.append(command)
    cmd.append("--help")

    help = (
        subprocess.check_output(cmd).decode().replace("usage: notefile.py", "usage: notefile")
    )  # long comment

    helpmd.append(
        f"""
```text
{help}
```"""
    )

with open("CLI_help.md", "wt") as f:
    f.write("\n\n".join(helpmd))
