
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

help = 'Dummy help wrong'
raise PluginError('Dummy help')

