
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError

if ask_help :
  help = """
  Template t <<_p.dest_name>> : 
%# for b, name in zip(_p.bits, _p.names):
  - <<'with' if b else 'without'>> <<name>> prefix
%# -
  """
  raise EndOfPlugin()

conf = C(
%# for b, name in zip(_p.bits, _p.names):
  <<name>>_prefix = << f"'_{name}.'" if b else 'None'>>,
%# -
)


