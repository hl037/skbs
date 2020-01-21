
import click
from contextlib import contextmanager

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
  
