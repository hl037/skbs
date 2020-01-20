
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  Template t OFrT : 
  - with opt prefix
  - with force prefix
  - without raw prefix
  - with template prefix
  """
  raise EndOfPlugin()

conf = C(
  opt_prefix = '_opt.',
  force_prefix = '_force.',
  raw_prefix = None,
  template_prefix = '_template.',
)


