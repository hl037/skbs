
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  help = """
  Template t
  """
  raise EndOfPlugin()

from tempiny import Tempiny

conf = C(
  tempiny=[
    ('*.c' , Tempiny.C),
    ('*.tex' , Tempiny.TEX),
    ('*' , Tempiny.PY),
  ],
  raw_prefix=None,
)


