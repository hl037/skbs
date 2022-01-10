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

LONG_DESC = read_file('README.md') + '\n\n' + read_file('HISTORY.rst')

EXTRAS = {}

setup(
    name='skbs',
    version='2.2.1',
    description='SKeleton BootStrap, a full-powered yet trivial to use and customize template based bootstrap or code generation tool',
    long_description=LONG_DESC,
    long_description_content_type='text/markdown',
    author='Léo Flaventin Hauchecorne',
    author_email='hl037.prog@gmail.com',
    url='https://github.com/hl037/skbs',
    license='GPLv3',
    packages=find_packages(),
    test_suite=None,
    include_package_data=True,
    zip_safe=False,
    install_requires=['click>=0.7', 'appdirs>=1.4.4', 'tempiny>=1.1'],
    test_requires=['pytest>=6.2.2', 'pytest_datadir_ng>=1.1.1', 'pytest-cov>=2.11.1'],
    extras_require=None,
    entry_points={
      'console_scripts':[
        'skbs=skbs.cli:main',
      ]
    },
    classifiers=[
        'Development Status :: 6 - Mature',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Other Scripting Engines',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Text Processing',
        'Topic :: Utilities',
    ],
    **EXTRAS
)

