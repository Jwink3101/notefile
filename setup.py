#!/usr/bin/env python
# -*- coding: utf-8 -*-

import notefile

from setuptools import setup

setup(
    name='notefile',
    py_modules=['notefile'],
    install_requires=[
        "ruamel.yaml"
    ],
    long_description=open('readme.md').read(),
    entry_points = {
        'console_scripts': ['notefile=notefile:cli'],
    },
    version=notefile.__version__,
    description='Create associated notefiles',
    url='https://github.com/Jwink3101/notefile',
    author=notefile.__author__,
    author_email='Jwink3101@@users.noreply.github.com',
    license='MIT',
)
