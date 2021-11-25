__doc__ = """
Template {{_p.dest}}
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

 ## if _p.click:
plugin = C()

@click.command(help=__doc__)
def main(**kwargs):
  plugin.update(kwargs)

with click.Context(main) as ctx:
  __doc__ = main.get_help(ctx)

if ask_help :
  raise EndOfPlugin()

invokeCmd(main, args)

 ## -
 ## else :
if ask_help :
  raise EndOfPlugin()

 ## -
