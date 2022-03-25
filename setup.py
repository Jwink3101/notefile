#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Cannot import notefile if the user doesn't have `install_requires`
# so instead read it from the the file itself. This is a bit hacky but works.
# And while eval is usually unsafe, I control the code it calls so it is fine

with open("notefile/__init__.py", "rt") as file:
    for line in file:
        line = line.strip()
        if line.startswith("__version__"):
            __version__ = line.split("=", 1)[1].strip()
            __version__ = eval(__version__)
            break
    else:
        raise ValueError("Could not find __version__ in source")

from setuptools import setup

setup(
    name="notefile",
    py_modules=["notefile"],
    install_requires=["ruamel.yaml"],
    long_description=open("readme.md").read(),
    entry_points={"console_scripts": ["notefile=notefile.cli:cli"],},
    version=__version__,
    description="Create associated notefiles (sidecar files)",
    url="https://github.com/Jwink3101/notefile",
    author="Justin Winokur",
    author_email="Jwink3101@@users.noreply.github.com",
    license="MIT",
    python_requires=">=3.8",
)
