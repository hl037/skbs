
HRPROTOPARSER
################

hrprotoparser is for "Human Readable PROTOcol PARSER"

Plugins
+++++++

Template file  syntax
=====================

The synthax used is the Tempiny one.
Basically, there are 3 contexts : 

Code context
------------

Each line starting by the code prefix (specified in __plugin.py, or '##' by default) is basically python code except for the block delimitation :
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
Basically, you can imagine (btw, this is really how it is implemented...) each Text context is like a call to ``print`` 

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
  ho it works

Expression context
------------------

Inside a Text context, you may want to print an expression (for example a variable value or the result of a python call etc.)
You can do it by surrounding it with the expression delimiters (specified in __plugin.py or '{{' and '}}' by default).
It will be replaced by the expression value at the time of execution. Example ::

  ## for i in range(3)
  Item number {{i}}
  ## -

Will print ::

  Item number 0
  Item number 1
  Item number 2

Any python code is here again allowed.

Once again, you sould only execute trusted templates.


Template plugin structure
=========================

A template plugin structure permits to define a generator, for a language or a documentation etc.

.. code-block::

   /template/
   | - plugin.py (optional)
   | - root/
   |   | - __include/ (optional)
   |   |   | - include_file1
   |   |   | - __template_include_file2
   |   |    \___
   |   | - file.c
   |   | - __template_file2.c
   |   |   | - subdir/
   |   |   | - __include/ (optional)
   |   |   |   | - include_file3
   |   |   |   | - __template_include_file4
   |   |   |    \___
   |   |    \___
   |   | - ...
   |    \___
    \___

It is a directory hierarchy with an optionnal __plugin.py that defines options of the template and functions usable in them.
Then all files starting by __template_<name> will be parsed and copied as <name> in the destination directory
All other files will be copied as is.

__plugin.py
-----------

This file should define the config and the functions accessible in the templates.
it can define a variable ``config`` which should be an ``hl037utils.config.Config`` providing the following settings ::

  from hl037utils.config import Config as C
  conf = C(
    tempiny = [
      (<glob_pattern>, C(
        stmt_line_start=r'//#'
        begin_expr='{{'
        end_expr='}}'
      )), # config for all files matching regex
      ...
      # any other config
    ]
  )

It can also provide a ``plugin`` variable that will be accessible using either ``plugin`` or ``_p`` in the tempalte. Any function, constant etc. defined on it will be accessible.

__template_*
------------

Template files to be executed. These are templte using the previously seen tempiny synthax.
Some python symbols are predefined : 

 * ``plugin`` or ``_p`` : plugin variable as defined in __plugin.py
 * ``proto`` : Protocol object (as defined in protocol_parser.py)

__include/ directory
--------------------

If an ``__include/`` is a child directory of a directory in the template, then all file in the parent directory and its children will be able to include any file of ``__include``, calling ``include(<path>)`` from an expression context.
Note that the ``__include/`` directory itself will not be copied to the destination. Also, inside ``__include/``, the same file prefix rules applies (``__template_name``).


API Reference
=============

Inside a code or expression context, you can use the following objects.

include(path)
-------------

Permits to include ``path``.

``path`` should be relatve to an ``__include/`` directory. It should be the real path (including the ``__template_`` prefixed if necessary).

Return : a str containing the content of the file, parsed if it begins with ``__template_``.

plugin
------

Variable defined inside ``__plugin.py``.

p
---

Same as ``plugin``




