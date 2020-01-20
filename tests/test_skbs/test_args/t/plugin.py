
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  Template t
  """
  raise EndOfPlugin()

plugin = C(
  a1 = args[0],
  a2 = args[1],
  d = dest
)

conf = C(
  raw_prefix=None
)


