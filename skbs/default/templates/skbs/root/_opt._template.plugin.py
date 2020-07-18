__doc__ = """
Template {{dest.parent.name}}
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

# conf = C(
#   # # Predefined template syntax are Tempiny.PY, Tempiny.C and Tempiny.TEX :
#   # # Tempiny.C  = dict(stmt_line_start=r'//#', begin_expr='{{be}}', end_expr='{{ee}}')
#   # # Tempiny.PY = dict(stmt_line_start=r'##', begin_expr='{{be}}', end_expr='{{ee}}')
#   # # Tempiny.TEX = dict(stmt_line_start=r'%#', begin_expr='<<', end_expr='>>')
#   # tempiny = [
#   #   ('*' : Tempiny.PY)
#   # ],
#   opt_prefix = '_opt.',
#   force_prefix = '_force.',
#   raw_prefix = '_raw.',
#   template_prefix = '_template.',
#   #   pathmod_filename = '__pathmod',
# )
# conf.dir_template_filename = conf.template_prefix

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

