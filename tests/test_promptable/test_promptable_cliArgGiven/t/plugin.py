
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

plugin = C()

app = cyclopts.App()
@app.default
@promptable
def main(service: Annotated[str, Prompt("Service name")]):
  plugin.service = service

if ask_help :
  raise EndOfPlugin()

invokeCmdCyclopts(app, args)
