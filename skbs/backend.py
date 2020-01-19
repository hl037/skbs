
from pathlib import Path
import traceback
from contextlib import contextmanager
from functools import wraps
from hl037utils.config import Config as C
import pkg_resources
import os
import shutil
from .pluginutils import EndOfPlugin
from tempiny import Tempiny
import io

#from dbug import *

from traceback import print_exc

import time
import json

APP = 'skbs'

class Include(object):
  """
  Include function implementation tracking the include paths
  """
  def __init__(self, include_paths, tempiny_l, base_locals, opt_prefix, template_prefix):
    self.include_paths = include_paths
    self.tempiny_l = tempiny_l
    self.base_locals = base_locals
    self.opt_prefix = opt_prefix
    self.template_prefix = template_prefix

  def __call__(self, path_str, **_locals):
    try:
      p = next( p for inc_p in reversed(self.include_paths) if (p := inc_p / path_str).is_file() )
    except StopIteration:
      raise FileNotFoundError(path_str)

    out_name, is_opt, is_template = Backend.parseFileName(p.name, self.opt_prefix, self.template_prefix)
    if is_opt :
      raise RuntimeError("An included file can't be optionnal")
    if is_template :
      tempiny = Backend.getFirstMatch(self.tempiny_l, p.with_name(out_name))
      _locals = C(**self.base_locals, **_locals)
      out = io.StringIO()
      with p.open('r') as in_f :
        Backend.processFile(tempiny, in_f, out, _locals, p, None)
      val = out.getvalue()
    else:
      val = p.read_text()
    # On unix-like system, a line must end with '\n'.
    # Since the included concent could be in the middle of a line, the extra '\n' should be removed
    if val[-1] == '\n' :
      return val[:-1] 
    return val

class Backend(object):
  OPT_PREFIX = '_opt.'
  TEMPLATE_PREFIX = '_template.'
  def __init__(self, config):
    self.config = config


  @staticmethod
  def createConfig(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), 'wb') as f :
      f.write(pkg_resources.resource_string(APP, 'default/conf.py'))

  def listTemplates(self):
    """
    List installed templates
    @return List[default_templates],List[templates]
    """
    default_dir = self.config.template_dir/'default/templates'
    user_dir = self.config.template_dir/'templates'
    return (
      [ p.name for p in default_dir.iterdir()] if default_dir.is_dir() else [],
      [ p.name for p in user_dir.iterdir()] if user_dir.is_dir() else []
    )

  def installDefaultTemplates(self):
    from distutils.dir_util import copy_tree
    self.config.template_dir.mkdir(parents=True, exist_ok=True)
    pkg_resources.set_extraction_path(self.config.template_dir)
    dest = str(self.config.template_dir/'default/templates/') + '/'
    src = pkg_resources.resource_filename(APP, 'default/templates/')
    if src != dest :
      copy_tree(src, dest)
    return dest

  def installTemplate(self, name, src):
    from distutils.dir_util import copy_tree
    dest = self.config.template_dir / 'templates' / name
    copy_tree(str(src), str(dest))
    return dest
  
  def uninstallTemplate(self, name):
    from distutils.dir_util import remove_tree
    dest = self.config.template_dir / 'templates' / name
    remove_tree(str(dest))
    return dest

  @staticmethod
  def parsePlugin(path, args, dest, ask_help):
    tempiny = None
    plugin = None
    g = C(
      args = args,
      ask_help = ask_help,
      C=C,
      EndOfPlugin=EndOfPlugin,
      inside_skbs_plugin=True,
      dest=dest if not ask_help else None,
    )
    if path.is_file() :
      # source plugin.py if one
      with path.open('r') as f :
        obj = compile(f.read(), path, 'exec')
      try:
        exec(obj, {}, g)
      except EndOfPlugin:
        pass
    conf = g.get('conf')
    plugin = g.get('plugin')
    help = g.get('help', 'No help provided for this template')
    return conf, plugin, help

  def parseConf(self, conf):
    tempiny = None
    
    if conf is None :
      conf = C()
    if 'tempiny' in conf :
      tempiny = [ (pattern, Tempiny(**c)) for pattern, c in conf.tempiny ]
    else:
      tempiny = [ ('*', Tempiny()) ]
    opt_prefix = conf.get('opt_prefix', self.OPT_PREFIX)
    template_prefix = conf.get('template_prefix', self.TEMPLATE_PREFIX)
    include_dirname = conf.get('include_dirname', self.TEMPLATE_PREFIX)
    return tempiny, opt_prefix, template_prefix
  
  def findTemplate(self, template):
    """
    Find `template`. If `template` starts with a '@', then search in globally installed template.
    Else, if the path exists and point to a directoryn, return this directory.

    @return Path object to template root
    """
    if template[0] == '@' :
      p = self.config.template_dir/'templates'/template[1:]
      if not p.is_dir() :
        p = self.config.template_dir/'default/templates'/template[1:]
    else:
      p = Path(template)
    if not p.is_dir() :
      raise FileNotFoundError(p)
    return p

  @staticmethod
  def processFile(tempiny, in_f, out_f, base_locals, in_p, out_p):
    _locals = C(**base_locals)
    _locals.dest = out_p
    _locals.parent = out_p.parent if out_p is not None else None
    template = tempiny.compile(in_f)
    template(out_f, {}, _locals)

  @staticmethod
  def getFirstMatch(l, path):
    """
    Get the second item of the first match on the frist item in a list of couples
    """
    return next(obj for glob_pat, obj in l if path.match(glob_pat))
  
  @staticmethod
  def parseFileName(filename, opt_prefix, template_prefix):
    """
    @return out_name, is_opt, is_template
    """
    out_name = filename
    is_template = False
    is_opt = False
    if out_name.startswith(opt_prefix) :
      is_opt = True
      out_name = out_name[len(opt_prefix):]
    if out_name.startswith(template_prefix) :
      is_template = True
      out_name = out_name[len(template_prefix):]
    return out_name, is_opt, is_template
  
  def execTemplate(self, template_path : Path, dest : str, args):
    from hl037utils.config import Config as C
    ask_help = (dest == '@help')
    conf, plugin, help = self.parsePlugin(template_path / 'plugin.py', args, dest, ask_help)
    if ask_help :
      return False, help
    dest = Path(dest)
    tempiny_l, opt_prefix, template_prefix = self.parseConf(conf)
    
    d = template_path / 'root'
    stack = [(False, d)]
    include_paths = []
    base_locals = C(
      plugin=plugin,
      _p=plugin,
    )
    base_locals.include = Include(include_paths, tempiny_l, base_locals, opt_prefix, template_prefix)
    while stack :
      
      seen, d = stack.pop()
      if seen :
        include_paths.pop()
        continue
      
      stack.append((True, d))
      include_paths.append(d/'__include')
      out = dest / d.relative_to(template_path / 'root')
      out.mkdir(parents=True, exist_ok=True)
      for in_p in d.iterdir() :
      
        if in_p.is_dir() :
          if in_p.name != '__include' :
            stack.append((False, in_p))
          continue
          
        out_name, is_opt, is_template = self.parseFileName(in_p.name, opt_prefix, template_prefix)
        
        out_p = out/out_name
        if is_opt :
          if out_p.exists() :
            continue
        if is_template :
          tempiny = self.getFirstMatch(tempiny_l, out_p)
          with in_p.open('r') as in_f, out_p.open('w') as out_f :
            self.processFile(tempiny, in_f, out_f,  base_locals, in_p, out_p)
        else:
          shutil.copyfile(in_p, out_p)
    return True, ''

