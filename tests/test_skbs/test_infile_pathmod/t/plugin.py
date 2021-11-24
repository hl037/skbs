"""
Template 
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  raise EndOfPlugin()

conf = C(
  raw_prefix = '_raw.',
)


