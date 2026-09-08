
import sys
from typing import Annotated

import cyclopts

from . import configutils
from . import pluginutils
from .backend import Backend, GitError
from pathlib import Path

app = cyclopts.App(
  name='skbs',
  help_epilogue=f'Global options:\n  -c, --config PATH  Override the default configuration path [default: {configutils.default_config}]',
)

config_path = None
B = None

def ensureB(f):
  from functools import wraps
  @wraps(f)
  def _f(*args, **kwargs):
    if B is None :
      print('You should first create the config')
      raise SystemExit(1)
    return f(*args, **kwargs)
  return _f

def confirm(prompt):
  try:
    return input(f'{prompt} [y/N]: ').strip().lower() in ('y', 'yes')
  except EOFError :
    return False

def _color(s, code):
  return f'\033[{code}m{s}\033[0m'

def _extractConfigOption(argv):
  """
  Pull -c/--config VALUE out of argv by hand, so cyclopts never sees it and
  never gets a chance to consume the following `--` (needed verbatim by
  `gen`'s own end_of_options_delimiter) while looking for -c/--config's own
  argument. `app.meta`'s variadic passthrough was tried and always strips
  the first `--` it sees, wherever it is in the stream.
  """
  config = configutils.default_config
  remaining = []
  it = iter(argv)
  for tok in it :
    if tok in ('-c', '--config') :
      config = next(it, config)
    else :
      remaining.append(tok)
  return config, remaining

def run(argv=None):
  global config_path, B
  if argv is None :
    argv = sys.argv[1:]
  config_path, argv = _extractConfigOption(argv)
  try:
    B = configutils.getBackend(config_path)
  except FileNotFoundError:
    pass
  app(argv)

@app.command(name='create-config')
def createConfig(path: str = configutils.default_config):
  """
  Create / reset to default the configuration file.
  """
  p = Path(path)
  if p.is_file() :
    if not confirm(f'The configuration file {path} already exists, are you sure you want to reset it to defaults ?'):
      raise SystemExit(0)
  Backend.createConfig(p)
  print(f'Default configuration file written at : {path}')

@app.command(name='config-path')
def configPath():
  """
  Prints the path to the in-use configuration file.
  """
  if B is None :
    print(config_path)
  else:
    print(B.config.config_path)

@app.command(name='install-defaults', alias='i-d')
@ensureB
def installDefaults(symlink: Annotated[bool, cyclopts.Parameter(name=['--symlink', '-s'])] = False):
  """
  Install default provided templates
  """
  f = B.installDefaultTemplates(symlink)
  print(f'Default templates installed at {f}')

@app.command(alias='i')
@ensureB
def install(
  src: str,
  symlink: Annotated[bool, cyclopts.Parameter(name=['--symlink', '-s'])] = False,
  name: Annotated[str | None, cyclopts.Parameter(name=['--name', '-n'])] = None,
):
  """
  Install a new template. `src` can be a local path, or a git URL to clone
  (installed under domain-name.com/path... unless --name is given).
  """
  if Backend.isGitUrl(src) :
    if symlink :
      print('--symlink is not supported when installing from a git URL')
      raise SystemExit(1)
    try:
      f = B.installTemplateFromGit(src, name)
    except GitError as err :
      print(err)
      raise SystemExit(1)
    print(f'{src} cloned and installed at {f}')
    return
  src_p = Path(src)
  if name is None :
    name = src_p.name
  f = B.installTemplate(name, src_p, symlink)
  print(f'{name} template installed at {f}')

@app.command(alias='u')
@ensureB
def uninstall(name: str):
  """
  Uninstall a template
  """
  f = B.uninstallTemplate(name)
  print(f'{name} uninstalled at {f}')

@app.command(name='list', alias=['l', 'ls'])
@ensureB
def listTemplates(*paths: str):
  """
  List installed templates. If paths are given, search from them instead of the installed ones.
  """
  if len(paths) == 0 :
    default, user = B.listTemplates()
    print()
    print(_color('User-installed templates :', 36))
    print('  ' + '\n  '.join(map(str, user)))
    print()
    print(_color('Default templates :', 36))
    print('  ' + '\n  '.join(map(str, default)))
  else:
    for p in paths :
      templates = B.findTemplates(Path(), p)
      print()
      print(_color(f'Templates found in {p} :', 36))
      print('  ' + '\n  '.join(map(str, templates)))
      print()

genApp = cyclopts.App(name='gen', end_of_options_delimiter='--')
app.command(genApp, alias='g')

@genApp.default
@ensureB
def gen(
  template: str,
  dest: str,
  *args: str,
  debug: Annotated[bool, cyclopts.Parameter(name=['--debug', '-g'])] = False,
  stdout: Annotated[bool, cyclopts.Parameter(help='Only for single file templates : output to stdout. --single-file is implied')] = False,
  single_file: Annotated[bool, cyclopts.Parameter(name=['--single-file', '-s'], help='Authorize single file template for non installed templates.')] = False,
):
  """
  Generate a skeleton from a template.

  Parameters
  ----------
  template: str
    if template starts with an '@', it will look for an installed template. Else, it will be considered as the template path.
  dest: str
    the output directory (parents will be created if needed)
  args: str
    argument passed to the template ( skbs gen <template_name> -- --help for more informations )
  """
  try:
    pluginutils.__name = f'skbs gen {template} {dest} --'
    template_path = B.findTemplate(template, single_file_authorized=single_file or stdout)
    out_f = None
    if stdout :
      out_f = sys.stdout
    res, help = B.execTemplate(template_path, dest, list(args), out_f)
    if not res :
      print(help)
  except:
    if debug :
      import pdb; pdb.post_mortem(sys.exc_info()[2])
    raise

completeApp = cyclopts.App(name='_complete-templates', show=False)
app.command(completeApp)

@completeApp.default
@ensureB
def completeTemplates(incomplete: str = ''):
  """
  (internal) Print template name completions for the given partial name, one per line.
  Used by the bash/zsh completion scripts, not meant to be called directly.
  """
  root_parts = incomplete.split('/')
  root = '/'.join(root_parts[:-1])
  candidates = B.findTemplates(Path(), root, rec=False, dirs=True)
  # Backend.findTemplates's "@..."-rooted branch returns candidates already
  # fully qualified with `root` baked in (e.g. root="@ns" -> "@ns/thing");
  # the plain-local-path branch (and the root=="" case, listing both @names
  # and local files) returns bare names relative to `root` instead, needing
  # it prepended back here to reconstruct the full completion.
  qualified = bool(root) and root.startswith('@')
  known_prefix = root + '/' if qualified else ''
  add_prefix = '' if (qualified or not root) else root + '/'
  for _p in candidates :
    p = str(_p)
    tail = p[len(known_prefix):] if p.startswith(known_prefix) else p
    if tail.startswith(root_parts[-1]) :
      print(f'{add_prefix}{p}')

# Kept as a plain list here (rather than introspecting cyclopts' private
# App._commands) so it stays trivially in sync with the @app.command(...)
# declarations above, without depending on cyclopts internals.
COMMAND_NAMES = (
  'create-config', 'config-path',
  'install-defaults', 'i-d',
  'install', 'i',
  'uninstall', 'u',
  'list', 'l', 'ls',
  'gen', 'g',
)

completeCommandsApp = cyclopts.App(name='_complete-commands', show=False)
app.command(completeCommandsApp)

@completeCommandsApp.default
def completeCommands(incomplete: str = ''):
  """
  (internal) Print command name completions for the given partial name, one per line.
  Used by the bash/zsh completion scripts, not meant to be called directly.
  """
  for name in COMMAND_NAMES :
    if name.startswith(incomplete) :
      print(name)

if __name__ == '__main__':
  run()
