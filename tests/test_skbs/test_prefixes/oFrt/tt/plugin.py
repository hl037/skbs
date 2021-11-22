
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  help = """
  Template tt oFrt : 
  - without opt prefix
  - with force prefix
  - without raw prefix
  - without template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = None,
  force_prefix = '_force.',
  raw_prefix = None,
  template_prefix = None,
)


