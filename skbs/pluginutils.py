
import click
from click.exceptions import Exit, Abort
from contextlib import contextmanager

from dbug import *

def tryImport(*args):
  try:
    return __import__(mod)
  except:
    return None

__click_sm_names = [
  '_bashcomplete',
  '_compat',
  '_termui_impl',
  '_textwrap',
  '_unicodefun',
  '_winconsole',
  'core',
  'decorators',
  'exceptions',
  'formatting',
  'globals',
  'parser',
  'termui',
  'testing',
  'types',
  'utils',
]

for sm in __click_sm_names:
  tryImport(f'click.{sm}')

__click_modules = [
  mod
  for sm in __click_sm_names
  if (mod := getattr(click, sm, None))
]

#Dvar(r"""__click_modules""")
__click_modules.append(click)

def nop(*args, **kwargs):
  pass

@contextmanager
def silentClick():
  echo = click.echo
  secho = click.secho
  for sm in __click_modules :
    sm.echo = nop
    sm.secho = nop
  try:
    yield
  finally:
    for sm in __click_modules :
      sm.echo = echo
      sm.secho = secho
    
  


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

class CliError(Exception):
  def __init__(self, ctx):
    self.ctx = ctx
    super()
  @classmethod
  def doRaise(cls, ctx, param, value):
    raise cls(ctx)

def __get_help_option(self, ctx):
  """Returns the help option object."""
  help_options = self.get_help_option_names(ctx)
  if not help_options or not self.add_help_option:
    return

  return click.Option(help_options, is_flag=True,
      is_eager=True, expose_value=False,
      callback=CliError.doRaise,
      help='Show this message and exit.')
  
__ctx = None
__name = '--'

def invokeCmd(cmd, args, **extra):
  """
  Invoke a click command, so that the usage will be adapted to fit the parent command if one.
  **extra are passed to cmd.make_context
  """
  try :
    with silentClick() :
      cmd.get_help_option = __get_help_option.__get__(cmd, cmd.__class__)
      ctx = cmd.make_context(__name, args, parent = __ctx, **extra)
      cmd.invoke(ctx)
  except Exit : 
    import pdb; pdb.xpm()
    pass
  except CliError as cli_err:
    raise PluginError(cli_err.ctx.get_help())
  except Exception :
    raise PluginError(ctx.get_help())
  

