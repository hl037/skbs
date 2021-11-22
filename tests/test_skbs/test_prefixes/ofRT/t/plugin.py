
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  help = """
  Template t ofRT : 
  - without opt prefix
  - without force prefix
  - with raw prefix
  - with template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = None,
  force_prefix = None,
  raw_prefix = '_raw.',
  template_prefix = '_template.',
)


