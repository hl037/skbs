
import os
import sys
import traceback
import click
import pkg_resources
import typing as t
from functools import wraps
from itertools import chain

from pathlib import Path

from . import configutils
from .backend import Backend, findTemplates

"""
Résolution algorithm :

Command names are split by dash, and a prefix tree is constructed in alias.
A tree is a list of tuple tuple ("name", sub_tree, cmd, i) where subtree is a tree, cmd is the command at this node, and i = 0, used later.

Search for exact match with full command name. If found, return the command
nodes = [aliases]
for i in range(len(cmd_name)):
  nodes = [ a for n, sub, cmd, j in nodes if cmd_name[i] == n[j] for a in chain(((n, sub, cmd, j+1),), sub) ]
if len(nodes) == 0 :
  return None
else:
  return nodes[1]
"""

def common_opts(*F):
  def composed(a):
    return reduce(lambda x, f: f(x), reversed(F), a)
  return composed

def _tree_nodes(t, fullname=None, level=-1):
  if fullname is None :
    return ( (name, *val, 0, name, level+1) for name, val in t.items() )
  return ( (name, *val, 0, f'{fullname}-{name}', level+1) for name, val in t.items() )

class AliasedGroup(click.Group):
  AliasTree = dict[str, ('AliasedGroup.AliasTree', click.Command | None)]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.aliases = {} # type: AliasedGroup.AliasTree

  def add_command(self, cmd: click.Command, name: t.Optional[str] = None) -> None:
    name = name or cmd.name
    rv = super().add_command(cmd, name)
    node = self.aliases 
    subs = name.split('-')
    for sub in subs[:-1]:
      node, *_ = node.setdefault(sub, ({}, None))
    sub, c = node.setdefault(subs[-1], ({}, cmd))
    if c is not cmd :
      node[subs[-1]] = (sub, cmd)
    return rv

  def get_command(self, ctx, cmd_name):
    rv = super().get_command(ctx, cmd_name)
    if rv is not None:
      return rv
    nodes = list(_tree_nodes(self.aliases))
    for l in cmd_name:
      nodes = [ a for n, sub, cmd, i, fn, level in nodes if l == n[i] for a in chain(((n, sub, cmd, i+1, fn, level),), _tree_nodes(sub, fn, level)) ]
    
    matches = [ (cmd, fn, level) for _, _, cmd, i, fn, level in nodes if i > 0 ]
    if len(matches) != 0 :
      m = max( level for _, _, level in matches)
      matches = [ (cmd, fn) for cmd, fn, level in matches if level == m ]
      if len(matches) != 1 :
        ctx.fail(f"Ambiguous command name : {' '.join(sorted(fn for _, fn in matches))}")
      return matches[0][0]

    unmatches = [ (cmd, fn, level) for _, _, cmd, i, fn, level in nodes if i == 0 ]
    if len(matches) != 0 :
      m = max( level for _, _, level in unmatches)
      matches = [ (cmd, fn) for cmd, fn, level in unmatches if level == m ]
      if len(matches) != 1 :
        ctx.fail(f"Ambiguous command name : {' '.join(sorted(fn for _, fn in matches))}")
      return matches[0][0]
        
    ctx.fail(f"Ambiguous command name : {' '.join(sorted(fn for *_, fn in nodes))}")

  def resolve_command(self, ctx, args):
    # always return the full command name
    _, cmd, args = super().resolve_command(ctx, args)
    return cmd.name, cmd, args

config_path = None
B = None

def ensureB(f):
  @wraps(f)
  def _f(*args, **kwargs):
    if B is None :
      click.secho('You should first create the config')
      exit(1)
    return f(*args, **kwargs)
  return _f

  

@click.command(cls=AliasedGroup)
@click.option('--config', '-c', type=click.Path(), default=configutils.default_config, help='Override the default configuration path')
def main(config):
  global config_path
  global B
  config_path = config
  try:
    B = configutils.getBackend(config)
  except FileNotFoundError:
    pass
  
@main.command(name='create-config')
@click.argument('path', required=False, default=configutils.default_config)
def createConfig(path):
  """
  Create / reset to default the configuration file.
  """
  p = Path(path)
  if p.is_file() :
    if not click.confirm(f'The configuration file {path} already exists, are you sure you want to reset it to defaults ?'):
      exit(0)
  Backend.createConfig(p)
  click.echo(f'Default configuration file written at : {path}')

@main.command(name='config-path')
def config_path():
  """
  Prints the path to the in-use configuration file. 
  """
  if B is None :
    click.secho(config_path)
  else:
    click.secho(B.config.config_path)


@main.command(name='install-defaults')
@click.option('--symlink', '-s', is_flag=True)
@ensureB
def installDefaults(symlink):
  """
  Install default provided templates
  """
  f = B.installDefaultTemplates(symlink)
  click.echo(f'Default templates installed at {f}')

@main.command(name='install')
@click.option('--symlink', '-s', is_flag=True)
@click.option('--name', '-n', type=str, default=None, required=False)
@click.argument('src', type=click.Path())
@ensureB
def install(src, name, symlink):
  """
  Install a new template.
  """
  src = Path(src)
  if name is None :
    name = src.name
  f = B.installTemplate(name, src, symlink)
  click.echo(f'{name} template installed at {f}')
  
@main.command(name='uninstall')
@click.argument('name')
@ensureB
def uninstall(name):
  """
  Uninstall a template
  """
  f = B.uninstallTemplate(name)
  click.echo(f'{name} uninstalled at {f}')

@main.command(name='list')
@click.argument('paths', nargs=-1)
@ensureB
def listTemplates(paths):
  """
  List installed templates. If paths are given, search from them instead of the installed ones.
  """
  se = click.secho
  if len(paths) == 0 :
    default, user = B.listTemplates()
    se('\n')
    se('User-installed templates :', fg='cyan', nl=False)
    se('\n  ', nl=False)
    se("\n  ".join(map(str, user)), fg='green', nl=False)
    se('\n\n', nl=False)
    se('Default templates :', fg='cyan', nl=False)
    se('\n  ', nl=False)
    se("\n  ".join(map(str, default)), fg='green', nl=False)
    se('\n')

  else:
    for p in map(Path, paths) :
      templates = findTemplates(p, p)
      se('\n')
      se(f'Templates found in {p} :', fg='cyan', nl=False)
      se('\n  ', nl=False)
      se("\n  ".join(map(str, templates)), fg='green', nl=False)
      se('\n\n', nl=False)
      


@main.command(name='gen')
@click.option('--debug', '-g', is_flag=True)
@click.argument('template', type=click.Path())
@click.argument('dest', type=str)
@click.option('--stdout', is_flag=True, help='Only for single file templates : output to stdout. --single-file is implied')
@click.option('--single-file', '-s', is_flag=True, help='Authorize single file template for non installed templates.')
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
@click.pass_context
@ensureB
def gen(ctx, debug, template, dest, stdout, single_file, args):
  """
  Generate a skeleton from a template.

  template : if template starts with an '@', it will look for an installed template. Else, it will be considered as the template path.
  dest : the output directory (parents will be created if needed)
  args : argument passed to the template ( skbs gen <template_name> -- --help for more informations )
  """
  try:
    from . import pluginutils
    pluginutils.__ctx = ctx
    pluginutils.__name = f'{template} {dest} --'
    template_path = B.findTemplate(template, single_file_authorized=single_file or stdout)
    out_f = None
    if stdout :
      out_f = sys.stdout
    res, help = B.execTemplate(template_path, dest, args, out_f)
    if not res :
      click.echo(help)
  except:
    if debug :
      import pdb; pdb.post_mortem(sys.exc_info()[2])
    raise

def bind_skip_after_double_dash_parse_args(cmd):
  ori = cmd.parse_args
  def parse_args(self, ctx, args):
    try:
      ind = args.index('--')
    except ValueError :
      ori(ctx, args)
      ctx.params['args'] = []
      return
    n_args = args[:ind]
    ret = ori(ctx, n_args)
    ctx.params['args'] = args[ind+1:]
    return ret
  cmd.parse_args = parse_args.__get__(cmd, cmd.__class__)
  return

try:
  bind_skip_after_double_dash_parse_args(gen)
except:
  import pdb; pdb.post_mortem(sys.exc_info()[2])
  raise


