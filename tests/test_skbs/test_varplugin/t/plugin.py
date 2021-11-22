
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

plugin = 42

conf = C(
  raw_prefix=None
)


