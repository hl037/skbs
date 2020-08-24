
SKBS
####

SKBS for SKeleton BootStrap

As a programmer I encounter many times moment where I'm telling myself "So boring to always copy-paste the same project"
and short after "Why is there no **SIMPLE** project generator based on simple template I can easily customize and create ???"

...Well I fed up...

...Now there is one. =)

What is SKBS
++++++++++++

Okay, so skbs was originally a python module with a command line interface permiting to bootstrap all the boiler plate of a project.
...Now, it can generate any kind of file structure dynamically...
First, you need to write a template (easy enough thanks to a built-in template to... bootstrap templates...),
then either use it passing its path, or install it (copy or symlink) to acces it with @<name>.

Then you call it and it's done.

Features
++++++++

* Static templates are as simple as the file they contain
* Easy to share templates
* Full python-powered template engine with ridiculous easy synthax
* Configurable template synthax (because double braces expression for latex is hellier than anything)
* Full python interpreter available inside a template
* Dynamic file names
* Dynamic directory names
* Click integration to do complex templates that need argument parsing
* Full-featured include system (because writing and maintaining the same header is non sense)
* Write your first template in less than 5 minutes
* Backend heavily tested with pytest unit tests

Install
+++++++

pip is the prefered way ::

   pip install skbs

Then, generate the first configuration file ::
   
   skbs create-config

It will display you the location of the installed templates.

By default, templates will be installed to the system's default location for application data (on linux, generaly ``~/.local/share/skbs/``).

Then, install the default templates ::

   skbs install-defaults

Usage
+++++

Usage ::

   Usage: skbs [OPTIONS] COMMAND [ARGS]...

   Options:
     -c, --config PATH  Overide the default configuration path
     --help             Show this message and exit.

   Commands:
     config-path       Prints the path to the in-use configuration file.
     create-config     Create / reset to default the configuration file.
     gen               Generate a skeleton from a template.
     install           Install a new template
     install-defaults  Install default provided templates
     list              List installed templates
     uninstall         Uninstall a template

Usage of gen ::
   
   Usage: skbs gen [OPTIONS] TEMPLATE DEST -- [ARGS]...
   
     Generate a skeleton from a template.
   
     template : if template starts with an '@', it will look for an installed
     template. Else, it will be considered as the template path. dest : the
     output directory (parents will be created if needed) args : argument
     passed to the template ( skbs gen <template_name> @help , or skbs gen <template_name> _ -- --help for more
     informations )
   
   Options:
     --help  Show this message and exit.

Example to generate the template for creating a skbs plugins ::

   skbs gen @skbs <dest>

The arguments and options after the double dash (``--``) are sent to the template. For example, for the skbs template ::

   Usage:  [OPTIONS]

     skbs Meta-Template =D This is the template to generate the base skeleton
     of a custom skbs template

   Options:
     --click             Generate click command bootstrap
     -s, --sft FILENAME
     --help              Show this message and exit.

The ``--click`` option adds a click command line parser to easily take options that are usable in the template.
The ``-s`` permits to generate a signle-file template, with only the file following the option.


Template engine
+++++++++++++++
The template engine used is tempiny.
By the way, the unit tests of skbs serves as tests for Tempiny. =)

See tempiny for more details. Here a summary of its features :

Template file syntax
=====================

The synthax used is the Tempiny one.

First an example to demonstrate all its features ::

   ## # need to declare variables that may be used in a generator as "globals" because of the behaviour as : https://stackoverflow.com/a/31298828/1745291
   ## global a, b, c
   
   This text will be printed as it is
   
   lines starting with '##' (or a user-configured prefix) are be python code.
   
   ## a=5 # this won't be printed
   ## # this is a comment in the python script. Won't be printed.
   
   if/else/for/while/with/try/except etc blocks don't need indentation. instead, a line containing only '## -' marks the block end.
   
   ## for i in range(a) :
   ##   b = a + 1 # you may indent
   ## c = a +2 # or not, still in the for block.
   This text will be printed 5 times (a = {{a}}) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{be}} and {{ee}}
   ##   for j in range(3) :
   You can also nest loops
   ##   -
   ## # ↑ end of inner loop
   ## -
   ## # end of outer loop
   
   Expression can be as complex you want as long as they are valid python expression returning something that can be transformed to a string :
   {{ ";".join( str(i) + f' - {a=},{b=},{c=}' for i in range(2)) }}

will be ouputed as ::

   This text will be printed as it is
   
   lines starting with '##' (or a user-configured prefix) are be python code.
   
   
   if/else/for/while/with/try/except etc blocks don't need indentation. instead, a line containing only '## -' marks the block end.
   
   This text will be printed 5 times (a = 5) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{ and }}
   You can also nest loops
   You can also nest loops
   You can also nest loops
   This text will be printed 5 times (a = 5) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{ and }}
   You can also nest loops
   You can also nest loops
   You can also nest loops
   This text will be printed 5 times (a = 5) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{ and }}
   You can also nest loops
   You can also nest loops
   You can also nest loops
   This text will be printed 5 times (a = 5) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{ and }}
   You can also nest loops
   You can also nest loops
   You can also nest loops
   This text will be printed 5 times (a = 5) Btw, between a double brace (2 '{'), you can put expression that will be converted to str, and printed instead.
   To escape it, two variables are defined by skbs (not tempiny) : `be` (begin of expression) and `ee` (end of expression) : {{ and }}
   You can also nest loops
   You can also nest loops
   You can also nest loops
   
   Expression can be as complex you want as long as they are valid python expression returning something that can be transformed to a string :
   0 - a=5,b=6,c=7;1 - a=5,b=6,c=7


Basically, there are 3 contexts : 

Code context
------------

Each line starting by the code prefix (specified in ``plugin.py``, or '##' by default) is basically python code except for the block delimitation :
in python, the indentation level delimits a block while with tempiny, for pratical use, indentation doesn't matter, and a block is ended by a single dash ( "-" ).

Example : 


.. code-block::

  ## a = 5
  ## for i in range(a) :
  ##   b = 2 + i
  ##   # Do come stuff
  ## c=3 # this is still in the for
  ## -
  ## # end of the for


Any python code is allowed. This is the reason you should use templates **only from trusted sources**.

Text context
------------

Any line that doesn't start with the code prefix is "text", and will be outputed as is each time the execution flow reaches it.
Basically, you can imagine (btw, this is actually how it is implemented...) each Text context is like a call to ``print`` 

For example, the following : 

.. code-block::

  This is a text
  ## for i in range(3):
  To see
  ## -
  how it works

Will output : 

.. code-block::

  This is a test
  To see
  To see
  To see
  how it works

Expression context
------------------

Inside a Text context, you may want to print an expression (for example a variable value or the result of a python call etc.)
You can do it by surrounding it with the expression delimiters (specified in ``plugin.py`` or '{{' and '}}' by default).
It will be replaced by the expression value at the time of execution. Example ::

  ## for i in range(3)
  Item number {{i}}
  ## -

Will print ::

  Item number 0
  Item number 1
  Item number 2

Any python cexpression is allowed.

Once again, you sould only execute trusted templates.

Template
++++++++

A plugin permits to define a file structure, that will be copied and parsed

Template directory structure
============================


.. code-block::

   /template/
   | - plugin.py (optional)
   | - root/
   |   | - __include/ (optional)
   |   |   | - _raw.include_file1
   |   |   | - _template.include_file2
   |   |    \___
   |   | - file.c
   |   | - __template_file2.c
   |   |   | - subdir/
   |   |   | - __include/ (optional)
   |   |   |   | - include_file3
   |   |   |   | - include_file4
   |   |   |    \___
   |   |    \___
   |   | - ...
   |    \___
    \___

It is a directory hierarchy with an optionnal ``plugin.py`` that defines options of the template and functions usable in them.
The directories, subdirectories and files under ``root`` are copied following the same structure (except for dynamic names, explained later).

A file name could have a first prefix, either ``_opt.`` or ``_forced.``, then a second either ``_raw.`` or ``_template.``.
*opt* is for "optional", if the file exists alread, it won't be overwritten.
*forced* is the opposite
*raw* means the file will be copied as is
*template* means the file will be parsed by tempiny.

In the output, the prefixes will obviously be removed from the name

if the first prefix is omited, *forced* is assumed, and if the second is ommited, *template* is assumed.
This behaviour and the prefixes can be changed.


Alternatively, a template could also be a single file template if ``root`` is a file instead of a directory.
In this case, the ``root`` file is the only file. It is considered *forced* and *template*. The ``is_opt`` can be set to change the *optional* flag from inside the template.
A directory ``__include`` can be present at the same level to include files in it from the template. A plugin.py can also be present to add more complexe logic.

This is the file tree structure of a single-file template : 

.. code-block::

   /template/
   | - plugin.py (optional)
   | - root
   | - __include/ (optional)
   |   | - _raw.include_file1
   |   | - _template.include_file2
   |    \___
    \___

``plugin.py``
-------------

This file is used to define the configuration and all the complex logic of the template, such as the option parser (click) and the function / variables available inside the template.

It can define a variable ``config`` which should be a ``skbs.pluginutils.Config`` (aliased as ``C`` without need for importing it)
providing the following settings ::

   conf = C(
     # Predefined template syntax are Tempiny.PY, Tempiny.C and Tempiny.TEX :
     # Tempiny.C  = dict(stmt_line_start=r'//#', begin_expr=', end_expr=')
     # Tempiny.PY = dict(stmt_line_start=r'##', begin_expr=', end_expr=')
     # Tempiny.TEX = dict(stmt_line_start=r'%#', begin_expr='<<', end_expr='>>')
     tempiny = [
       ('*' : Tempiny.PY),
     ],
     opt_prefix = '_opt.',
     force_prefix = '_force.',
     raw_prefix = '_raw.',
     template_prefix = '_template.',
     pathmod_filename = '__pathmod',
   )
   conf.dir_template_filename = conf.tamplte_prefix

``conf.tempiny`` permits to change the Tempiny dialect for files matching the pattern in the first element of the pair. The second argument is the dialect. ``Tempiny`` is already defined in the scope, no need for importing it. 

if the *opt* prefix is defined as ``""`` or ``None``, files without prefix will be considered optional and to force overwrite, they should have the *force* prefix. 
The same applies for *raw*

It can also provide a ``plugin`` variable that could be anything and will be define in the templates' scope as ``plugin`` and ``_p``. Any function, constant etc. defined on it will be accessible. It is recommanded to define it as a ``skbs.pluginutils.Confg`` (or simply ``C``)

An instance of ``C`` behave like a ``dict`` with the values accessible as attributes ::

   c = C(a=5, b=6)
   c['a'] # == 5
   c.b # == 6

it implements the dict interface. (see the source code for more details)

You can add a docstring at the start of the file to provide an help message when the user ask for the plugin help.

Alternatively, you can also define locally (without ``global`` statement) a variable ``help`` containing this message (the first method is the recommended one though).

You may also call ``endOfPlugin`` to stop the execution without error,

or raise ``PluginError(<help msg>)`` if an error occured.


If the click flag was passed when bootstraping the template, a click command line is added. To add user passed variable to the template via _p.<var_name>, just add it as an option ::


   plugin = C()

   @click.command(help=__doc__)
   @click.option('--auther')  #  <--- Here is an option. its vallue is available with _p.author
   def main(**kwargs):
     plugin.update(kwargs)

   with click.Context(main) as ctx:
     __doc__ = main.get_help(ctx)

   if ask_help :
     raise EndOfPlugin()

   invokeCmd(main, args)



Template files
--------------

Template files are files starting with the ``conf.template_prefix`` defined in ``plugin.py``. These are template using the previously seen tempiny synthax.
Some python symbols are predefined : 

 * ``plugin`` or ``_p`` : reference to the ``plugin`` variable as defined in ``plugin.py``
 * ``dest`` : The destination file of the template

(see the Reference ofr more details)

Sections
--------

A template can define sections to overwrite only some parts of a file.

Depending of the value of ``keep_only_sections``, either the template will replace only the sections of an existing file, or, it will keep only the sections.
In both cases, you can decide which section is overriten or not.

A section is delimited by a call to ``beginSection()`` and ``endSection()``. (see the reference for more details).
Sections are retrieved in the existing file using some pattern matching, either static (the ``n`` following line of ``beginSection()`` of preceeding ``endSection()``), or dynamic (using a callback).

Section not found are added at a ``placeholder()``. It is matched the same way as a seciton.

Example ::

   beginSection(placeholder='pl')
   //START OF THE SECTION
   
   section content
   
   //END OF THE SECTION
   endSection()
   
   ...Some content...
   
   placeholder('pl')
   //PLACEHOLDER

..."section content" will replace whatever is between "//START OF THE SECTION" and "//END OF THE SECTION" in the existing file. if not found but there is a "//PLACEHOLDER" line, then it will be placed just before.

include(path, \*\*kwargs) -> str
--------------------------------

An ``include(path, **kwargs)`` function is provided in the templates scope. It will search for any ``__include/path`` file existing in any parent directory. inside an ``__include`` directory, the prefixes *raw* and *template* workxs, but not the *opt* and *force* ones.
Any kwargs will be accessible from the included template as global variable, and can be modified.

This function returns the output of the included file (it is commonly used as an inline expression)


Dynamic filename
----------------

Inside a template, one can define the local variable ``new_path`` that will contain the new path for the file, relative to the destination.
The easiest way is by doing ::

   ## new_path = dest.with_name('new_name')

You can also cancel the execution of the file template, and decide to exclude it by calling ``exclude()`` inside.

Providing a ``new_path`` of ``None`` has the same effect but won't stop the file template execution.

Dynamic dirname
---------------

The same applies for directories, except you have to define a special file in it called the same as the *template* prefix alone, or the default *template* ("``_template.``") if the *template* is set to ``None`` or an empty string.
This file should be raw python (no "## " prefixes).

Click integration
-----------------

Click is already available in the scope without need for importing it. To use it to parse the args, inspire you from this example ::

   plugin = C()
   
   @click.command()
   @click.option('--name', '-n', type=str, prompt=True) # prompt=True will prompt the value if not provided
   @click.option('--with_db/--no-db', prompt=True)
   def main(**kwargs):
     plugin.update(kwargs)
   
   invokeCmd(main, args) # invoke the click command this way makes it behave nicely with skbs

...This code is all that is needed

the default @skbs template provides the click boiler plate to handle the --help option

User API Reference
++++++++++++++++++


plugin.py
=========

Symbols available in plugin.py and symbols you can define

args : [arg1, arg2, ...]
------------------------

Argument list for the template. basically everything follownig the double dash ( ``--`` ) in the command line.

ask_help : bool
---------------

If ``--help`` was passed as first argument or dest is ``@help``, then this flag will be set.
The plugin is then expected to define a ``__doc__`` variable (automatic with a *docstring* as file header) or a ``help`` variable.

C : <class skbs.pluginutils.Config>
-----------------------------------

``skbs.pluginutils.Config`` class alias to create quickly dict-compatible javascript-like object objects. 

click : <module click>
----------------------

``click`` module as if you imported it with ``import click``. Permits to define advance CLI-like argument parser (see Click integration)

invokeCmd(cmd, args)
--------------------

Invoke a click command with args as if they came from a command line. You should not call yourself a click command and always use this function, since it does some handling of click exceptions and file redirection to get the usage string.

EndOfPlugin : Exception
-----------------------

You should raise this exception as you would use a ``return`` if you were in a function : it will stop the plugin.py execution without an error and start parsing the template.

Could be used if ask_help is true to return immediately (dont forget to either put a *docstring* or a define a ``help`` variable...

PluginError : Exception
-----------------------

Raise it to inform skbs an error occured (for example incompatible argments). You should pass to it as first argument the help message.

pluginError(help_msg)
---------------------

Shortcut to raise a PluginError

inside_skbs_plugin : bool
-------------------------

Will be set to ``True`` when the plugin is called from skbs, else, it won't be define.

As a *Best-practice*, you can use this snippet to prevent execution of the plugin outside skbs ::

   try:
     inside_skbs_plugin
   except:
     from skbs.pluginutils import IsNotAModuleOrScriptError
     raise IsNotAModuleOrScriptError()

Note : it is already included in the skbs plugin template

Tempiny : <class Tempiny>
-------------------------

Tempiny as if you had imported it like ::

   from tempiny import Tempiny

Used to pass configuration and change the dialect depending to the file pattern.

dest : str
----------

root output directory


---------------------------------------

conf = ...
----------

User defined configuration. Use the following structure ::

   conf = C(
     # Predefined template syntax are Tempiny.PY, Tempiny.C and Tempiny.TEX :
     # Tempiny.C  = dict(stmt_line_start=r'//#', begin_expr=', end_expr=')
     # Tempiny.PY = dict(stmt_line_start=r'##', begin_expr=', end_expr=')
     # Tempiny.TEX = dict(stmt_line_start=r'%#', begin_expr='<<', end_expr='>>')
     tempiny = [
       ('*' : Tempiny.PY), # '*' : glob-like pattern, Tempiny dialect to use if a file match the pattern
       # ...
     ],
     opt_prefix = '_opt.', # if a file starts with this prefix, it will not overwrite an existing file
     force_prefix = '_force.', # if a file starts with this prefix, it will overwrite an existing file
     raw_prefix = '_raw.', # if a file starts with this prefix, it will be copied as is
     template_prefix = '_template.', # if a file starts with this prefix, it will be parsed by Tempiny
     pathmod_filename = '__pathmod.py', # file name for pathmod scripts (always prefer in template new_path to change file name / location)
   )
   conf.dir_template_filename = conf.tamplte_prefix

__doc__ = ...
-------------

Prefer a header *docstring* that python will automatically recognize and assign this variable with. Script documentation.

Note : with click integration, the command usage will be used instead of this variable.

help = ...
----------

Same as ``__doc__``. Prefer ``__doc__``

plugin = ...
------------

This variable will be available everywhere else under the reference ``_p`` and ``plugin``.


---------------------------------------


Template files
==============

plugin
------

Alias for the ``plugin`` variable defined in ``plugin.py``.

_p
---

Same as plugin, another shorter alias.

dest : pathlib.Path
-------------------

Relative to destination repository current file template path.

C : <class skbs.pluginutils.Config>
-----------------------------------

``skbs.pluginutils.Config`` class alias to create quickly dict-compatible javascript-like object objects. 

include(path)
-------------

Permits to include ``path``.

``path`` should be relatve to an ``__include/`` directory. It should be full relative real to ``__include`` path (including the ``_template.`` prefixed if necessary).

Return : a str containing the content of the file, parsed if it begins with ``__template_``.

Hint : use if in an expression ::

{{include('_template.file.py')}}

exclude()
---------

To abort reading the current file template, so that this file will not be copied to the destination.

endOfTemplate()
---------------

Same as function return : stop reading the template here, but keep and copy to destination what has been read.

beginSection(n=1, f=None, placeholder=None, overwrite=True)
-----------------------------------------------------------

Start an overwritten section.
``f`` a calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.

If ``f`` is None, Then the ``n`` following lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the section start.

If a placeholder is specified and the original file does not have this section, then it will be put just before the placeholder (so that further added sections go always to the end)

if ``overwrite`` is set, then the section from the replaced output file will be overitten, else, it will be kept.

endSection(n=1, f=None)
-----------------------

End an overwritten section.
``f`` is a calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.

If ``f`` is None, Then the ``n`` previous lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the section end.

placeholder(name, n=1, f=None)
------------------------------

Defines a placeholder

``name`` is the name of the placeholder
``f`` is a calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.

If ``f`` is None, Then the ``n`` next lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the placeholder.


sls, be, ee
-----------

Tempiny token configuration : 
- sls : Stmt_Line_Start
- be : Begin of Expression
- ee : End of Expression

---------------------------------------

new_path = ...
--------------

Path in the destination directory the file should have.
Tipically used like this to rename dynaically the file ::

   ## new_path = dest.with_name('new_name')

is_opt = ...
--------------

Changes the *optionnal* aspect of the template. Overrides the prefix in the template file name

use_sections = ...
------------------

If true force usage of sections. If None, use section if at least one section is defined. (default : None)

keep_only_sections = ...
------------------------

If true, will overwrite the original only keeping its sections, else, only the sections will be replaced in the original file. (default : True)
 
---------------------------------------
  
_template. (or what ``conf.dir_template_filename`` contains)
============================================================

This file is read as python code (not tempiny).

The same symbols than in file templates are defined except include.

Permit to define ``new_path`` for a directory. ``exclude()`` works also to prevent it to be copied (and entered).

---------------------------------------

Included templates
==================

Same as regular files except ``dest`` is not defined and ``exclude()`` will exclude file template being parsed.

---------------------------------------

__pathmod.py
============

Used in previous version to chane file name. Always prefer new_path variable in each template instead

removePrefix(p:Pathlib.Path) -> pathlib.Path
--------------------------------------------

Function to remove prefixes from the filename 

---------------------------------------

pathmod(path:pathlib.Path) -> (keep:bool, new_path:pathlib.Path)
----------------------------------------------------------------

User defined function to change file output path and 

this input path has the prefix, the function should return the new path with no prefix,  where the path should be generated.

License
+++++++

Copyright © 2018-2020 Léo Flaventin Hauchecorne

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

