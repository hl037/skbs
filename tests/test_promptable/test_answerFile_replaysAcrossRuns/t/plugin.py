
try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError()

plugin = C()

app = cyclopts.App()
@app.default
@answer_file('.skbs_answer')
@promptable
def main(
  replicas: Annotated[int, cyclopts.Parameter(name=['--replicas'])] = 1,
  *,
  service: Annotated[str, Prompt("Service name")],
):
  plugin.service = service
  plugin.replicas = replicas

if ask_help :
  raise EndOfPlugin()

invokeCmdCyclopts(app, args)
