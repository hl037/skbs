"""Dummy help"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

help='Wrong help'

if ask_help :
  raise EndOfPlugin()

# conf = C(
#   #   Predefined template syntax are Tempiny.PY, Tempiny.C and Tempiny.TEX :
#   #   Tempiny.C  = dict(stmt_line_start=r'//#', begin_expr=', end_expr=')
#   #   Tempiny.PY = dict(stmt_line_start=r'##', begin_expr=', end_expr=')
#   #   Tempiny.TEX = dict(stmt_line_start=r'%#', begin_expr='<<', end_expr='>>')
#   # tempiny = [
#   #   ('*' : Tempiny.PY)
#   # ],
#   opt_prefix = '_opt.',
#   force_prefix = '_force.',
#   raw_prefix = '_raw.',
#   template_prefix = '_template.',
#   #   pathmod_filename = '__pathmod',
# )
# conf.dir_template_filename = conf.tamplte_prefix


