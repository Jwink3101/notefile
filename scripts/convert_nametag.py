"""
Convert from filename_[tag1,tag2].ext format to notefile
"""

import sys
import os
import re
import shutil

# sys.path.append(os.path.abspath('..'))
import notefile

print(notefile.__version__)  # 20200103


SOURCE = "/full/path/to/source"

retags = re.compile("^(.*)[\_|-][\[|\(](.*?)[\]|\)]$")


def get_tag(filename):
    """
    Return: ( [[tag1,...,tagN], nontagname)

    Tags are in their "strip"ed format (lowercase and with _)
    """
    base, ext = os.path.splitext(filename)

    try:
        nontagname, tagsfull = retags.findall(base)[0]
    except IndexError:  # No tags
        return list(), filename

    tags = tagsfull.split(",")

    return tags, nontagname + ext


for root, dirs, files in os.walk(SOURCE):
    for item in dirs[:]:
        if item.startswith("."):
            dirs.remove(item)

    for file in files:
        if file.startswith("."):
            continue

        file = os.path.join(root, file)

        if os.path.islink(file):
            continue

        tags, newname = get_tag(file)
        if len(tags) == 0:
            continue

        shutil.move(file, newname)

        # Call the CLI since it will do a lot of this work for you
        cmd = ["tag"]
        for tag in tags:
            cmd.extend(["--tag", tag])
        cmd.append(newname)

        notefile.cli(cmd)
