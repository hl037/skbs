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

if sys.version_info < (3,):
    EXTRAS['use_2to3'] = True

setup(
    name='hrprotoparser',
    version='0.1.dev1',
    description='Human Readable protocol parser',
    long_description=LONG_DESC,
    author='Léo Flaventin Hauchecorne',
    author_email='hl037.prog@gmail.com',
    url='https://gitea.dev.leo-flaventin.com/hl037/hrprotoparser',
    license='Faites votre choix',
    packages=find_packages(),
    test_suite=None,
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    extras_require=None,
    entry_points={
      'console_scripts':[
        'hrprotoparser=hrprotoparser.cli:main',
      ]
    },
    #package_data={
    #  'module' : ['module/path/to/data', 'path/to/glob/*'],
    #},
    classifiers=[],
    **EXTRAS
)
