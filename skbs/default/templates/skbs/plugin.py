__doc__ = """
skbs Meta-Template =D
This is the template to generate the base skeleton of a custom skbs template
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError


conf = C(
  tempiny = [
    ('*', dict(stmt_line_start=r' ##', begin_expr='{{', end_expr='}}'))
  ],
)

plugin = C()

import click
from pathlib import Path
from skbs.backend import tempinySyntaxRegex
import re
from tempiny import Tempiny

@click.command(help=__doc__)
@click.option('--click', '-c', is_flag=True, help='Generate click command bootstrap')
@click.option('--sft', '-s', is_flag=True, help='Generate a single file template')
@click.option('--src', '-i', type=str, default=None, help='The source file for the content of the single file template')
def main(src, **kwargs):
  sft = kwargs['sft']
  plugin.update(kwargs)
  plugin.dest = dest
  if sft:
    if (
      (src and (src := Path(src)).is_file()) or
      (src := dest).is_file()
    ) :
      with open(sft_src, 'r') as f :
        plugin.content = f.readall()
    else :
      plugin.content = None

with click.Context(main) as ctx:
  __doc__ = main.get_help(ctx)

if ask_help :
  raise EndOfPlugin()

invokeCmd(main, args)


