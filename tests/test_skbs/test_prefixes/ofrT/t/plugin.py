
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  help = """
  Template tt ofrT : 
  - without opt prefix
  - without force prefix
  - without raw prefix
  - with template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = None,
  force_prefix = None,
  raw_prefix = None,
  template_prefix = '_template.',
)

