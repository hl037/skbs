#!/usr/bin/env python
import sys

from setuptools import setup, find_packages


def read_file(name):
    """
    Read file content
    """
    f = open(name)
    try:
        return f.read()
    except IOError:
        print("could not read %r" % name)
        f.close()

LONG_DESC = read_file('README.rst') + '\n\n' + read_file('HISTORY.rst')

EXTRAS = {}

setup(
    name='skbs',
    version='1.0',
    description='SKeleton BootStrap, a full-powered yet trivial to use and customize template based bootstrap tool',
    long_description=LONG_DESC,
    author='Léo Flaventin Hauchecorne',
    author_email='hl037.prog@gmail.com',
    url='https://gitea.dev.leo-flaventin.com/hl037/hrprotoparser',
    license='GPLv3',
    packages=find_packages(),
    test_suite=None,
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    extras_require=None,
    entry_points={
      'console_scripts':[
        'skbs=skbs.cli:main',
      ]
    },
    #package_data={
    #  'module' : ['module/path/to/data', 'path/to/glob/*'],
    #},
    classifiers=[],
    **EXTRAS
)
