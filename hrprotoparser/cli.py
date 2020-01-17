
import os
import sys
import traceback
import click
import click_completion
import pkg_resources
from functools import wraps

click_completion.init()

from pathlib import Path

from . import configutils
from .backend import Backend

#from dbug import *

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
@ensureB
def installDefaults():
  """
  Install default provided templates
  """
  f = B.installDefaultTemplates()
  click.echo(f'Default templates installed at {f}')

@click.argument('src-directory')
@click.argument('name')
@main.command(name='install')
@ensureB
def install(name, src_directory):
  """
  Install a new template
  """
  f = B.installTemplate(name, src_directory)
  click.echo(f'{name} template installed at {f}')
  
@click.argument('name')
@main.command(name='uninstall')
def uninstall(name):
  """
  Uninstall a template
  """
  f = B.uninstallTemplate(name)
  click.echo(f'{name} uninstalled at {f}')

@click.argument('protocol', type=click.File('r'))
@main.command(name='parse')
def parse(protocol):
  """
  Print everything parsed from the protocol
  """
  p = B.parseProtocol(protocol, protocol.name)
  click.echo(repr(p))
    
