
import io
import click
from click.exceptions import Exit, Abort, ClickException
from contextlib import contextmanager
from ._internal_click_monkey_patches import CliError

from dbug import *

class EndOfPlugin(Exception):
  pass

class IsNotAModuleOrScriptError(Exception):
  def __init__(self):
    super('This file is not a module or a script. It is an skbs plugin. It should only be used through skbs.')

class PluginError(Exception):
  """
  Used to dignal an error when executing the plugin.
  To be Instanciated passing the help string.
  """
  def __init__(self, help):
    super()
    self.help = help
  
__ctx = None
__name = '--'

def invokeCmd(cmd, args, **extra):
  """
  Invoke a click command, so that the usage will be adapted to fit the parent command if one.
  **extra are passed to cmd.make_context
  """
  from ._internal_click_monkey_patches import __get_help_option, silentClick
  stderr = io.StringIO()
  with silentClick(stderr):
    try :
      ctx = cmd.make_context(__name, args, parent = __ctx, **extra)
      cmd.invoke(ctx)
    except Exit : 
      pass
    except ClickException as exc : 
      exc.show(file=stderr)
    except Exception :
      import pdb; pdb.xpm()
      raise PluginError(ctx.get_help())
  err = stderr.getvalue()
  if err :
    raise PluginError(err)
  

