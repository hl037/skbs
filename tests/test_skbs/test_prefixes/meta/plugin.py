
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

if ask_help :
  help = """
  Template meta
  """
  raise EndOfPlugin()

from tempiny import Tempiny as T

conf = C(
  opt_prefix = None,
  force_prefix = None,
  template_prefix = None,
  raw_prefix = '___raw.',
  tempiny = [
    ('*', T.PY)
  ],
)

plugin = C.fromDict({c.lower() : c.isupper() for c in dest})
plugin.dest_name = dest
plugin.bits = [c.isupper() for c in dest]
plugin.names = ['opt', 'force', 'raw', 'template']

