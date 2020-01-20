
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  Template t OfRt : 
  - with opt prefix
  - without force prefix
  - with raw prefix
  - without template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = '_opt.',
  force_prefix = None,
  raw_prefix = '_raw.',
  template_prefix = None,
)


