
# Naming convention used throughout this file: a `_p` suffix means "Path
# object". `in_p` is a source/template path, `out_p` an output path (either
# relative to a destination root still to be joined, or already joined,
# depending on the function — see each call site).

import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from traceback import print_exc

import click

from .pluginutils import Config as C, EndOfPlugin, PluginError, exclude, pluginError, endOfTemplate, invokeCmd, OptionParser
from .pathresolve import (
  findTemplates, tempinySyntaxRegex, parseFilePath, FileNameParser,
  OPT_PREFIX, TEMPLATE_PREFIX, FORCE_PREFIX, RAW_PREFIX, INCLUDE_DIRNAME, PATHMOD_FILENAME,
)
from .pluginloader import parsePlugin, parseConf
from .fileengine import Include, processFile, processDir, parsePathMod, FileGlobals


@dataclass
class SingleFileGlobals:
  """
  Fixed contract of names for a single-file template: unlike multi-file
  templates, there's no separate plugin.py step, so this flattens the union
  of PluginGlobals + FileGlobals into the one namespace the file sees.
  Note it does NOT include `Tempiny` (PluginGlobals does) — single-file
  templates have never exposed it, kept as-is to not change behavior.
  """
  args: list[str]
  ask_help: bool
  C: type
  click: object
  invokeCmd: Callable
  EndOfPlugin: type[Exception]
  PluginError: type[Exception]
  pluginError: Callable
  dest: Path | None
  parseCmd: OptionParser
  inside_skbs_plugin: bool
  plugin: C
  _p: C
  removePrefix: Callable
  file_name_parser: FileNameParser
  exclude: Callable
  endOfTemplate: Callable
  invokeTemplate: Callable

sys.excepthook = print_exc

APP = 'skbs'

class Backend(object):
  # Kept as class attributes for backward compatibility; the canonical
  # values live in pathresolve.py.
  OPT_PREFIX = OPT_PREFIX
  TEMPLATE_PREFIX = TEMPLATE_PREFIX
  FORCE_PREFIX = FORCE_PREFIX
  RAW_PREFIX = RAW_PREFIX
  INCLUDE_DIRNAME = INCLUDE_DIRNAME
  PATHMOD_FILENAME = PATHMOD_FILENAME
  def __init__(self, config):
    self.config = config


  @staticmethod
  def createConfig(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), 'wb') as f :
      f.write(resources.files(APP).joinpath('default/conf.py').read_bytes())

  def listTemplates(self):
    """
    List installed templates
    @return List[default_templates],List[templates]
    """
    default_templates = self.default_templates
    user_templates = self.user_templates
    return (
      list(findTemplates(Path(), default_templates, sft=True)) if default_templates.is_dir() else [],
      list(findTemplates(Path(), user_templates, sft=True)) if user_templates.is_dir() else []
    )

  def findTemplates(self, path:str|Path, root:str|Path, rec=True, dirs=False, sft=False):
    root = str(root)
    if not root :
      yield from (f'@{p}' for p in findTemplates(Path(), self.default_templates, rec, dirs, True))
      yield from (f'@{p}' for p in findTemplates(Path(), self.user_templates, rec, dirs, True))
      yield from findTemplates(Path(), Path(), rec, dirs, sft)
      return
    elif root[0] == '@' :
      yield from (f'@{p}' for p in findTemplates(Path(root[1:]), self.default_templates, rec, dirs, True))
      yield from (f'@{p}' for p in findTemplates(Path(root[1:]), self.user_templates, rec, dirs, True))
      return
    else :
      yield from findTemplates(Path(), Path(root), rec, dirs, sft)

  @property
  def default_templates(self):
    return self.config.template_dir / 'default/templates'

  @property
  def user_templates(self):
    return self.config.template_dir / 'templates'


  def installDefaultTemplates(self, symlink=False):
    dest = str(self.default_templates) + '/'
    src = str(resources.files(APP).joinpath('default/templates/'))
    if src != dest :
      dest_p = Path(dest)
      if dest_p.exists() :
        if dest_p.is_symlink():
          dest_p.unlink()
        else:
          shutil.rmtree(dest)

      if symlink :
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        dest_p.symlink_to(src)
      else :
        self.config.template_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, dirs_exist_ok=True)
    return dest

  def installTemplate(self, name, src, symlink=False):
    dest = self.user_templates / name
    if dest.exists() :
      self.uninstallTemplate(name)
    if symlink :
      dest.parent.mkdir(parents=True, exist_ok=True)
      dest.symlink_to(src.absolute())
    else :
      if src.is_dir():
        shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
      else :
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)

    return dest

  def uninstallTemplate(self, name):
    dest = self.user_templates / name
    if dest.is_dir() and not dest.is_symlink() :
      shutil.rmtree(str(dest))
    else :
      dest.unlink()
    return dest

  def findTemplate(self, template, single_file_authorized=False):
    """
    Find `template`. If `template` starts with a '@', then search in globally installed template.
    Else, if the path exists and point to a directory, return this directory.

    @return Path object to template root
    """
    if template[0] == '@' :
      p = self.user_templates/template[1:]
      if not p.exists() :
        p = self.default_templates/template[1:]
    else:
      p = Path(template)
    if single_file_authorized and p.is_file() :
      return p
    if not p.is_dir() :
      if not p.is_file() :
        raise FileNotFoundError(p)
      return p
    return p

  def execSingleFileTemplate(self, template_path : Path, dest : str, args:list[str], out_f=None, plugin = C()):
    ask_help = (dest == '@help') or (args and args[0] == '--help')
    if dest == '@' :
      dest = Path(template_path.name)
      out_p = dest
      dest_parent = Path()
    else:
      dest = Path(dest)
      out_p = Path(dest.name)
      dest_parent = dest.parent

    # Template as file
    if template_path.is_file() :
      if dest.is_dir() : # TODO: test it properly
        dest_parent = dest
        dest = dest / template_path.name # if the dest is a directory, then we should use the same name as the template file...
        out_p = Path(dest.name)
      with open(template_path, 'r') as f :
        l = next(f)
      m = re.fullmatch(tempinySyntaxRegex, l)
      if m :
        conf = C(
          tempiny = [
            ('*', dict(stmt_line_start=m[1], begin_expr=m[2], end_expr=m[3]))
          ]
        )
      else :
        conf = C()

      tempiny_l, file_name_parser, include_dirname, pathmod_filename = parseConf(conf)

      base_locals = C(**vars(SingleFileGlobals(
        args = args,
        ask_help=ask_help,
        C=C,
        click=click,
        invokeCmd = invokeCmd,
        EndOfPlugin=EndOfPlugin,
        PluginError=PluginError,
        pluginError=pluginError,
        dest=dest if not ask_help else None,
        parseCmd=OptionParser(args, plugin),
        inside_skbs_plugin=True,
        plugin=plugin,
        _p=plugin,
        removePrefix=file_name_parser,
        file_name_parser=file_name_parser,
        exclude=exclude,
        endOfTemplate=endOfTemplate,
        invokeTemplate=self.invokeTemplate,
      )))

      try:
        _locals = processFile(template_path, out_p, False, True, base_locals, tempiny_l, dest_parent, out_f=out_f)
      except PluginError as err:
        return False, err.help
      return True, _locals.get('help')

    # Template as dir
    else:
      try:
        conf, plugin, help = parsePlugin(template_path / 'plugin.py', args, dest, ask_help, self.invokeTemplate)
      except PluginError as err:
        return False, err.help
      dest = Path(dest)

      tempiny_l, file_name_parser, include_dirname, pathmod_filename = parseConf(conf)

      base_locals = C(**vars(FileGlobals(
        plugin=plugin,
        _p=plugin,
        C=C,
        removePrefix=file_name_parser,
        file_name_parser=file_name_parser,
        exclude=exclude,
        endOfTemplate=endOfTemplate,
        invokeTemplate=self.invokeTemplate,
      )))
      base_locals.include = Include([template_path / '__include'], tempiny_l, base_locals, file_name_parser)

      processFile(template_path/'root', out_p, False, True, base_locals, tempiny_l, dest_parent, out_f=out_f)
      return True, help


  def execTemplate(self, template_path : Path, dest : str, args, out_f=None):
    """
    Generate `template_path` (single-file or multi-file, see
    execSingleFileTemplate) to `dest`. `dest` is `'@help'` (or `args[0] ==
    '--help'`) to only retrieve the help message without generating
    anything, or `'@'` to write a single-file template's output to `out_f`
    instead of the filesystem (unavailable for multi-file templates).

    @return (success: bool, help_or_error_message: str)
    """
    if not (template_path/'root').is_dir() :
      return self.execSingleFileTemplate(template_path, dest, args, out_f=out_f)

    if dest == '@' or out_f is not None:
      return False, 'Stream output is not available as dest for multi-file plugins.'
    ask_help = (dest == '@help') or (args and args[0] == '--help')
    try:
      conf, plugin, help = parsePlugin(template_path / 'plugin.py', args, dest, ask_help, self.invokeTemplate)
    except PluginError as err:
      return False, err.help
    dest = Path(dest)

    tempiny_l, file_name_parser, include_dirname, pathmod_filename = parseConf(conf)

    src_root = template_path / 'root'
    include_paths = []
    pathmod_stack = []
    base_locals = C(**vars(FileGlobals(
      plugin=plugin,
      _p=plugin,
      C=C,
      removePrefix=file_name_parser,
      file_name_parser=file_name_parser,
      exclude=exclude,
      endOfTemplate=endOfTemplate,
      invokeTemplate=self.invokeTemplate,
    )))
    base_locals.include = Include(include_paths, tempiny_l, base_locals, file_name_parser)

    stack = [(False, src_root, Path(''))]
    while stack :

      seen, src, out = stack.pop()
      if seen :
        include_paths.pop(0)
        if pathmod_stack :
          if pathmod_stack[0][1] <= 0 :
            pathmod_stack.pop(0)
          else:
            pathmod_stack[0][1] -= 1
        continue

      (dest / out).mkdir(parents=True, exist_ok=True)
      stack.append((True, src, out))
      pathmod = parsePathMod(src / '__pathmod.py', base_locals)
      if pathmod is None :
        if pathmod_stack:
          pathmod_stack[0][1] += 1
      else:
        pathmod_stack.insert(0, [pathmod, 0])
      include_paths.insert(0, src/'__include')
      (dest / out).mkdir(parents=True, exist_ok=True)

      for in_p in src.iterdir() :
        if in_p.name in ('__pathmod.py', file_name_parser.dir_template_filename) :
          continue
        if in_p.is_dir() :
          if in_p.name != '__include' :
            out_path = parseFilePath(out / in_p.name, file_name_parser, ( pm for pm, _ in pathmod_stack ), is_dir=True)
            out_path = processDir(base_locals, in_p, out_path, file_name_parser)
            if not out_path :
              continue
            stack.append((False, in_p, out_path))
          continue

        out_p, is_opt, is_template = parseFilePath(out / in_p.name, file_name_parser, ( pm for pm, _ in pathmod_stack ))
        if not out_p :
          continue
        processFile(in_p, out_p, is_opt, is_template, base_locals, tempiny_l, dest)
    return True, help

  def invokeTemplate(self, template_name, dest, args, out_f=None, single_file_authorized=None):
    """
    Resolve `template_name` (via findTemplate) and execTemplate it to
    `dest`. This is the function exposed as `invokeTemplate(...)` inside
    plugin.py/per-file templates (see pluginloader.parsePlugin).
    """
    if single_file_authorized is None :
      single_file_authorized = out_f is not None
    return self.execTemplate(self.findTemplate(template_name, single_file_authorized=single_file_authorized), dest, args, out_f)
