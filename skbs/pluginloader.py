
"""
Loading a template's plugin.py and parsing its conf: dynamic module
execution and the resulting namespace's contract.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from importlib.machinery import ModuleSpec, SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

import cyclopts
from tempiny import Tempiny

from .pluginutils import (
  Config as C, EndOfPlugin, PluginError, pluginError, invokeCmd, invokeCmdCyclopts,
  OptionParser, getClick, extractHelpFromLocals,
)
from .pathresolve import (
  FileNameParser, OPT_PREFIX, FORCE_PREFIX, RAW_PREFIX, TEMPLATE_PREFIX,
  INCLUDE_DIRNAME, PATHMOD_FILENAME, _get,
)


@dataclass
class PluginGlobals:
  """
  Fixed contract of names skbs injects into plugin.py's namespace. Plugins
  add further names at runtime (`conf`, `plugin`/`_p`, `help`...), which is
  why the actual runtime namespace stays a `Config` (dict-like) built from
  `vars(this)`, not this dataclass directly — it only documents/types the
  part skbs itself guarantees.
  """
  args: list[str]
  ask_help: bool
  C: type
  click: object
  cyclopts: object
  invokeCmd: Callable
  invokeCmdCyclopts: Callable
  EndOfPlugin: type[Exception]
  PluginError: type[Exception]
  pluginError: Callable
  inside_skbs_plugin: bool
  Tempiny: type
  invokeTemplate: Callable
  dest: Path | None
  parseCmd: OptionParser


def createPluginModule(path, g):
  """
  Create the module for the plugin, then execute it. `path` should be the path to the parent directory.
  """
  # Create a package to be able to import other modules from the plugin.
  # TODO: replace all non authorized characters be _
  package_name = '__skbs_plugin__' + str(path).replace('/', '_').replace('.','_').replace('-', '_')
  package_spec = ModuleSpec(package_name, None, origin=str(path))
  package_spec.submodule_search_locations = [str(path)]
  package_module = module_from_spec(package_spec)
  sys.modules[package_name] = package_module

  # Create the true plugin module
  name = f'{package_name}.plugin'
  loader = SourceFileLoader(name, str(path / 'plugin.py'))
  spec = spec_from_loader(name, loader)
  module = module_from_spec(spec)
  sys.modules[name] = module
  module.__dict__.update(g)

  try:
    loader.exec_module(module)
  finally:
    # Sync back whatever the plugin set before raising (e.g. EndOfPlugin
    # early-exit after assigning `help`).
    g.update(module.__dict__)
  return module.__dict__

def parsePlugin(path, args, dest, ask_help, invoke_template):
  """
  Load and run `path`'s plugin.py (if any), gathering `conf`/`plugin`/`help`
  from the resulting namespace. `invoke_template` is the Backend's
  invokeTemplate, wired here so plugins can call `invokeTemplate(...)`
  relative to their own `dest`.
  """
  plugin = None
  def invokeTemplate(_template_name, _dest, _args):
    invoke_template(_template_name, str(Path(dest)/_dest), _args)
  g = C(**vars(PluginGlobals(
    args = args,
    ask_help = ask_help,
    C=C,
    click=getClick(),
    cyclopts=cyclopts,
    invokeCmd = invokeCmd,
    invokeCmdCyclopts = invokeCmdCyclopts,
    EndOfPlugin=EndOfPlugin,
    PluginError=PluginError,
    pluginError=pluginError,
    inside_skbs_plugin=True,
    Tempiny=Tempiny,
    invokeTemplate=invokeTemplate,
    # Root output directory as given on the CLI: never resolved to an
    # absolute path by skbs. To make it available to the per-file
    # templates below (where `dest` means something else, see
    # tempinyFile), plugins are expected to copy it onto `plugin`/`_p`,
    # e.g. `plugin.dest = dest` (see default template plugin.py).
    dest=Path(dest) if not ask_help else None,
    parseCmd=OptionParser(args, plugin),
  )))
  if path.is_file() :
    # source plugin.py if one
    try:
      g.update(createPluginModule(path.parent, g))
    except EndOfPlugin:
      pass
  help = extractHelpFromLocals(g)
  if ask_help :
    raise PluginError(help)
  conf = g.get('conf')
  plugin = g.get('plugin', None)
  if plugin is None :
    plugin = g.get('_p')
  return conf, plugin, help

def parseConf(conf):
  tempiny_l = None

  if conf is None :
    conf = C()
  if 'tempiny' in conf :
    tempiny_l = [ (pattern, Tempiny(**c)) for pattern, c in conf.tempiny ]
  else:
    tempiny_l = [ ('*', Tempiny()) ]

  file_name_parser = FileNameParser(
    _get(conf, 'opt_prefix', OPT_PREFIX),
    _get(conf, 'force_prefix', FORCE_PREFIX),
    _get(conf, 'raw_prefix', RAW_PREFIX),
    _get(conf, 'template_prefix', TEMPLATE_PREFIX),
    conf.get('dir_template_filename', None),
  )
  include_dirname = conf.get('include_dirname', INCLUDE_DIRNAME)
  pathmod_filename = conf.get('pathmod_filename', PATHMOD_FILENAME)
  return tempiny_l, file_name_parser, include_dirname, pathmod_filename
