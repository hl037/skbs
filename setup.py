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
    version='1.0.1',
    description='SKeleton BootStrap, a full-powered yet trivial to use and customize template based bootstrap or code generation tool',
    long_description=LONG_DESC,
    long_description_content_type='text/x-rst',
    author='Léo Flaventin Hauchecorne',
    author_email='hl037.prog@gmail.com',
    url='https://github.com/hl037/skbs',
    license='GPLv3',
    packages=find_packages(),
    test_suite=None,
    include_package_data=True,
    zip_safe=False,
    install_requires=['click>=0.7', 'appdirs>=1.4.4', 'tempiny>=1.0'],
    extras_require=None,
    entry_points={
      'console_scripts':[
        'skbs=skbs.cli:main',
      ]
    },
    classifiers=[],
    **EXTRAS
)

