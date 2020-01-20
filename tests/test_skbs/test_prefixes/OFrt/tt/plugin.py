
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  Template tt OFrt : 
  - with opt prefix
  - with force prefix
  - without raw prefix
  - without template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = '_opt.',
  force_prefix = '_force.',
  raw_prefix = None,
  template_prefix = None,
)


