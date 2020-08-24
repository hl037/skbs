
import sys
import click
from contextlib import contextmanager

def tryImport(*args):
  try:
    return __import__(mod)
  except:
    return None

# termui is used to implement prompt
__click_sm_names = [
  '_bashcomplete',
  '_compat',
  #'_termui_impl',
  '_textwrap',
  '_unicodefun',
  '_winconsole',
  'core',
  'decorators',
  'exceptions',
  'formatting',
  'globals',
  'parser',
  #'termui',
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

__click_modules.append(click)

class Echo(object):
  def __init__(self, stderr):
    self._echo = click.echo
    self._secho = click.secho
    self.stderr = stderr
  def echo(self, message=None, file=sys.stdout, nl=True, err=False, color=None):
      return self._echo(message, self.stderr, nl, False, color)

  def secho(self, message=None, file=sys.stdout, nl=True, err=False, color=None, **styles):
      return self._secho(message, self.stderr, nl, False, color, **styles)
    
    

@contextmanager
def silentClick(stderr):
  new_echo = Echo(stderr)
  for sm in __click_modules :
    sm.echo = new_echo.echo
    sm.secho = new_echo.secho
  try:
    yield
  finally:
    for sm in __click_modules :
      sm.echo = new_echo._echo
      sm.secho = new_echo._secho

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
  
