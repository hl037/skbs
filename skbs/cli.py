
import os
import sys
import traceback
import click
import pkg_resources
from functools import wraps

from pathlib import Path

from . import configutils
from .backend import Backend, findTemplates

def common_opts(*F):
  def composed(a):
    return reduce(lambda x, f: f(x), reversed(F), a)
  return composed

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

  

@click.group()
@click.option('--config', '-c', type=click.Path(), default=configutils.default_config, help='Overide the default configuration path')
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
@click.option('--symlink', is_flag=True)
@ensureB
def installDefaults(symlink):
  """
  Install default provided templates
  """
  f = B.installDefaultTemplates(symlink)
  click.echo(f'Default templates installed at {f}')

@main.command(name='install')
@click.option('--symlink', is_flag=True)
@click.option('--name', '-n', type=str, default=None, required=False)
@click.argument('src-directory', type=click.Path())
@ensureB
def install(src_directory, name, symlink):
  """
  Install a new template.
  """
  src_directory = Path(src_directory)
  if name is None :
    name = src_directory.name
  f = B.installTemplate(name, src_directory, symlink)
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
      import sys
      out_f = sys.stdout
    res, help = B.execTemplate(template_path, dest, args, out_f)
    if not res :
      click.echo(help)
  except:
    if debug :
      import pdb; pdb.xpm()
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
  import pdb; pdb.xpm()
  raise


