__doc__ = """
skbs Meta-Template =D
This is the template to generate the base skeleton of a custom skbs template
"""

try:
  inside_skbs_plugin
except:
  from skbs.pluginutils import IsNotAModuleOrScriptError
  raise IsNotAModuleOrScriptError


conf = C(
  tempiny = [
    ('*', dict(stmt_line_start=r' ##', begin_expr='{{', end_expr='}}'))
  ],
)

plugin = C()

from typing import Annotated, Optional
from pathlib import Path
from skbs.backend import tempinySyntaxRegex
import re
from tempiny import Tempiny

app = cyclopts.App(help=__doc__)

@app.default
def main(
  src: Annotated[Optional[str], cyclopts.Parameter(name=['--src', '-i'])] = None,
  use_click: Annotated[bool, cyclopts.Parameter(name=['--click', '-c'])] = False,
  use_cyclopts: Annotated[bool, cyclopts.Parameter(name=['--cyclopts'])] = False,
  use_promptable: Annotated[bool, cyclopts.Parameter(name=['--promptable', '-p'])] = False,
  sft: Annotated[bool, cyclopts.Parameter(name=['--sft', '-s'])] = False,
):
  plugin.click = use_click
  plugin.cyclopts = use_cyclopts
  plugin.promptable = use_promptable
  plugin.sft = sft
  plugin.dest = dest
  if sft:
    if (
      (src and (src := Path(src)).is_file()) or
      (src := dest).is_file()
    ) :
      with open(src, 'r') as f :
        plugin.content = f.read()
    else :
      plugin.content = None

__doc__ = extractHelp(app)

if ask_help :
  raise EndOfPlugin()

invokeCmdCyclopts(app, args)
