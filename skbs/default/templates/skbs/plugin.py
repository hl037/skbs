
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  skbs Meta-Template =D
  This is the template to generate the base skeleton of a custom skbs template
  """
  raise EndOfPlugin()

