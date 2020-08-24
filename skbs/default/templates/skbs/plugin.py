__doc__ = """
skbs Meta-Template =D
This is the template to generate the base skeleton of a custom skbs template
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

plugin = C()

import click

@click.command(help=__doc__)
@click.option('--click', is_flag=True, help='Generate click command bootstrap')
@click.option('--sft', '-s', type=click.File('r'), default=None)
def main(sft, **kwargs):
  plugin.update(kwargs)
  if sft is not None :
    plugin.sft = sft.read()
  else:
    plugin.sft = None

with click.Context(main) as ctx:
  __doc__ = main.get_help(ctx)

if ask_help :
  raise EndOfPlugin()

invokeCmd(main, args)


