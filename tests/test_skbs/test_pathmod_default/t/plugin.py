
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

conf = C(
  pathmod_filename='__pathmod2.py',
)

plugin = C(
  a=42
)

