
from pathlib import Path
import traceback
from contextlib import contextmanager
from functools import wraps
import pkg_resources
import os
import shutil
from .pluginutils import Config as C, EndOfPlugin, PluginError, ExcludeFile, exclude, pluginError, endOfTemplate, invokeCmd
from tempiny import Tempiny
from itertools import accumulate, chain
import io
import click

from traceback import print_exc

import time
import json

APP = 'skbs'

class FlagPluginNotParsed(object):
  pass

class Include(object):
  """
  Include function implementation tracking the include paths
  """
  def __init__(self, include_paths, tempiny_l, base_locals, file_name_parser):
    self.include_paths = include_paths
    self.tempiny_l = tempiny_l
    self.base_locals = base_locals
    self.file_name_parser = file_name_parser

  def __call__(self, path_str, **_locals):
    try:
      p = next( p for inc_p in self.include_paths if (p := inc_p / path_str).is_file() )
    except StopIteration:
      raise FileNotFoundError(path_str)

    out_path, is_opt, is_template = Backend.parseFilePath(p, self.file_name_parser, None)

    if is_opt :
      raise RuntimeError("An included file can't be optionnal")
    if is_template :
      tempiny = Backend.getFirstMatch(self.tempiny_l, out_path)
      _locals = C(**self.base_locals, **_locals)
      out = io.StringIO()
      with p.open('r') as in_f :
        _locals, exc = Backend.tempinyFile(tempiny, in_f, out, _locals, p, None)
        if exc :
          try :
            raise exc
          except EndOfPlugin:
            pass
          except ExcludeFile:
            return ''
      val = out.getvalue()
    else:
      val = p.read_text()
    # On unix-like system, a line must end with '\n'.
    # Since the included concent could be in the middle of a line, the extra '\n' should be removed
    if val[-1] == '\n' :
      return val[:-1] 
    return val
  
class FileNameParser(object):
  """
  Remove template, opt or raw prefixes
  """
  def __init__(self, opt_prefix, force_prefix, raw_prefix, template_prefix, dir_template_filename = None):
    self.opt_prefix = opt_prefix
    self.force_prefix = force_prefix
    self.template_prefix = template_prefix
    self.raw_prefix = raw_prefix 
    if dir_template_filename is not None :
      self.dir_template_filename = dir_template_filename
    else :
      self.dir_template_filename = template_prefix
      if self.dir_template_filename is None :
        self.dir_template_filename = Backend.TEMPLATE_PREFIX
        

  def parse(self, name:str):
    is_opt = False
    is_raw = False
    # See the Karnaugh table
    if self.opt_prefix :
      if is_opt := name.startswith(self.opt_prefix) :
        name = name[len(self.opt_prefix):]
      elif self.force_prefix :
        if name.startswith(self.force_prefix) :
          name = name[len(self.force_prefix):]
    elif self.force_prefix :
      if not (is_opt := (not name.startswith(self.force_prefix))) :
        name = name[len(self.force_prefix):]
      
      
    if self.raw_prefix :
      if is_raw := name.startswith(self.raw_prefix) :
        name = name[len(self.raw_prefix):]
      elif self.template_prefix :
        if name.startswith(self.template_prefix) :
          name = name[len(self.template_prefix):]
    elif self.template_prefix :
      if not (is_raw := (not name.startswith(self.template_prefix))) :
        name = name[len(self.template_prefix):]

    is_template = not is_raw
      
    return name, is_opt, is_template
    
  
  def __call__(self, p:Path):
    p, _, _ = self.parse(p)
    return p

class OutStream(object):
  """
  Tempiny out stream to handle sections
  """
  class AlreadyInSectionError(RuntimeError):
    pass

  class PlaceholderWithKeepOnlySections(RuntimeError):
    pass

  @staticmethod
  def matcher(m_lines, begin):
    if begin :
      def match(lines, i):
        return lines[i:i+len(m_lines)] == m_lines
    else :
      def match(lines, i):
        return lines[i-len(m_lines):i] == m_lines
    return match

  class Section(object):
    """
    Section in a file
    """
    def __init__(self, placeholder, overwrite):
      self.placeholder = placeholder
      self.overwrite = overwrite
      self.begin_line = None
      self.end_line = None
      self.ori_begin_line = None
      self.ori_end_line = None
      self.begin = None
      self.end = None

    def __repr__(self):
      return f'Section(placeholder={self.placeholder}, overwrite={self.overwrite}, bl={self.begin_line}, el={self.end_line}, o_bl={self.ori_begin_line}, o_el={self.ori_end_line}, b={self.begin}, e={self.end})'

  class Placeholder(object):
    """
    
    """
    def __init__(self, name, f, begin_line):
      self.name = name
      self.f = f
      self.begin_line = begin_line
      self.ori_end_line = begin_line
      self.ori_begin_line = None
      self.ori_end_line = None
      self.sections = []
      self.begin = f
      self.end = lambda *args, **kwargs:True

    def __repr__(self):
      return f'Placeholder(name={self.name}, f={self.f}, bl={self.begin_line}, o_bl={self.ori_begin_line}, n_sec={len(self.sections)})'
      
  def __init__(self):
    self.lines = []
    self.sections = []
    self.cur_section = None
    self._placeholders = []
    self.placeholders = []

  def beginSection(self, n=1, f=None, placeholder=None, overwrite=True):
    """
    Start an overwritten section.
    @param f : A calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.
    @param n : If ``f`` is None, Then the ``n`` following lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the section start.
    @param placeholder If a placeholder is specified and the original file does not have this section, then it will be put just before the placeholder (so that further added sections go always to the end)
    """
    if self.cur_section is not None :
      raise OutStream.AlreadyInSectionError("Sections cannot be nested")
    self.cur_section = OutStream.Section(placeholder, overwrite), len(self.lines), n, f


  def endSection(self, n=1, f=None):
    """
    End an overwritten section.
    @param f : ``f`` is a calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.
    @param n : If ``f`` is None, Then the ``n`` previous lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the section end.
    """
    section, i, n, f_s = self.cur_section
    end = len(self.lines)
    if f_s is None :
      f_s = self.matcher(self.lines[i:i+n], begin=True)
    if f is None :
      f = self.matcher(self.lines[end-n:end], begin=False)
    section.begin = f_s
    section.end = f
    section.begin_line = i
    section.end_line = end
    self.cur_section = None
    self.sections.append(section)
  
  def placeholder(self, name, n=1, f=None):
    """
    Defines a placeholder
    @param name : name of the placeholder
    @param f : ``f`` is a calback function ``f(lines, i)`` where ``lines`` is a list of the lines in the original file. The function should return true if it matches.

    @param n : If ``f`` is None, Then the ``n`` previous lines in the "virtually" outputed template (as if it were run for the first time) will be the line to match exactly in the original file to tag the placeholder.
    """
    if self.cur_section is not None :
      raise OutStream.AlreadyInSectionError("A placeholder cannot be placed inside a section")
    self.sections.append((name, len(self.lines), n, f))
  
  def write(self, s):
    self.lines.extend(s.split('\n')[:-1])
  
  def getvalue(self):
    return "\n".join(self.lines) + '\n'

  def newPlacehoder(self, name, i, n, f, /, keep_only_sections):
    if keep_only_sections :
      raise self.PlaceholderWithKeepOnlySections("No placeholder can be set if `keep_only_sections` is True") 
    return self.Placeholder(name, f if f else self.matcher(self.lines[i:i+n], begin=True), i)
  
  def end(self, out_p, use_sections, keep_only_sections):
    """
    End the stream by handling the sections
    """
    if use_sections is None :
      use_sections = bool(self.sections)
    if not use_sections :
      return

    with open(out_p) as f :
      lines = [ l[:-1] for l in f ]
    
    candidate_sections = [ s if isinstance(s, self.Section) else self.newPlacehoder(*s, keep_only_sections=keep_only_sections) for s in self.sections ]
    
    sections = []
    # match sections in any order
    I = iter(range(len(lines)))
    for i in I:
      j, s = next(
        (
          (j, s) for j, s in enumerate(candidate_sections) if s.begin(lines, i)
        ),
        (None, None)
      )
      if j is not None :
        s.ori_begin_line = i
        candidate_sections.pop(j)
        for i in I :
          if s.end(lines, i) :
            s.ori_end_line = i
            sections.append(s)
            break
    # Remaining sections are the one not matched
    pldict = { pl.name : pl for pl in sections if isinstance(pl, self.Placeholder) }
    

    if keep_only_sections :
      # Replace sections in template with original file ones, except if overwrite
      for s in reversed(self.sections) :
        if not s.overwrite :
          self.lines[s.begin_line:s.end_line] = lines[s.ori_begin_line:s.ori_end_line]
    else:
      # Merge placeholders and sections
      # elements = sorted(chain(pldict.values(), sections), key=lambda x : x.ori_begin_line, reverse=True)
      # Place not matched sections in their placeholder
      for s in ( s for s in candidate_sections if isinstance(s, self.Section) ):
        pl = pldict.get(s.placeholder)
        if pl is not None :
          pl.sections.append(s)
      # Replace sections in original file file with template ones except if overwrite False (in this case, only add at placeholder if not present)
      
      for e in reversed(sections) :
        if isinstance(e, self.Section) :
          s = e
          if s.overwrite :
            lines[s.ori_begin_line:s.ori_end_line] = self.lines[s.begin_line:s.end_line]
        elif isinstance(e, self.Placeholder) :
          pl = e
          lines[pl.ori_begin_line:pl.ori_begin_line] = sum(( self.lines[s.begin_line:s.end_line] for s in pl.sections ), [])
      # Assign original file lines
      self.lines = lines
  def close(self):
    self.lines.clear()
    self.sections.clear()
    self.placeholders.clear()
    self._placeholders.clear()
    self.cur_section = None


class Backend(object):
  OPT_PREFIX = '_opt.'
  TEMPLATE_PREFIX = '_template.'
  FORCE_PREFIX = '_force.'
  RAW_PREFIX = '_raw.'
  INCLUDE_DIRNAME = '__include'
  PATHMOD_FILENAME = '__pathmod.py'
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

  def installDefaultTemplates(self, symlink=False):
    dest = str(self.config.template_dir/'default/templates/') + '/'
    src = pkg_resources.resource_filename(APP, 'default/templates/')
    if src != dest :
      dest_p = Path(dest)
      if dest_p.exists() :
        if dest_p.is_symlink():
          dest_p.unlink()
        else:
          from distutils.dir_util import remove_tree
          remove_tree(dest)

      if symlink :
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        dest_p.symlink_to(src)
      else :
        from distutils.dir_util import copy_tree
        self.config.template_dir.mkdir(parents=True, exist_ok=True)
        pkg_resources.set_extraction_path(self.config.template_dir)
        copy_tree(src, dest)
    return dest

  def installTemplate(self, name, src, symlink=False):
    dest = self.config.template_dir / 'templates' / name
    if dest.exists() :
      self.uninstallTemplate(name)
    if symlink :
      dest.parent.mkdir(parents=True, exist_ok=True)
      dest.symlink_to(src.absolute())
    else :
      from distutils.dir_util import copy_tree
      copy_tree(str(src), str(dest))
    return dest
  
  def uninstallTemplate(self, name):
    dest = self.config.template_dir / 'templates' / name
    if dest.is_symlink() :
      dest.unlink()
    else :
      from distutils.dir_util import remove_tree
      remove_tree(str(dest))
    return dest

  def parsePlugin(self, path, args, dest, ask_help):
    tempiny = None
    plugin = None
    def invokeTemplate(_template_name, _dest, _args):
      self.invokeTemplate(_template_name, str(Path(dest)/_dest), _args)
    g = C(
      args = args,
      ask_help = ask_help,
      C=C,
      click=click,
      invokeCmd = invokeCmd,
      EndOfPlugin=EndOfPlugin,
      PluginError=PluginError,
      pluginError=pluginError,
      inside_skbs_plugin=True,
      Tempiny=Tempiny,
      invokeTemplate=invokeTemplate,
      dest=dest if not ask_help else None,
    )
    if path.is_file() :
      # source plugin.py if one
      with path.open('r') as f :
        obj = compile(f.read(), path, 'exec')
      try:
        exec(obj, g.asDict(), g)
      except EndOfPlugin:
        pass
    help = next(( h for k in ('__doc__', 'help') if (h := g.get(k)) ), 'No help provided for this template' ) 
    if ask_help :
      raise PluginError(help)
    conf = g.get('conf')
    plugin = g.get('plugin')
    return conf, plugin, help

  def parseConf(self, conf):
    tempiny_l = None
    
    if conf is None :
      conf = C()
    if 'tempiny' in conf :
      tempiny_l = [ (pattern, Tempiny(**c)) for pattern, c in conf.tempiny ]
    else:
      tempiny_l = [ ('*', Tempiny()) ]
    file_name_parser = FileNameParser(
      conf.get('opt_prefix', self.OPT_PREFIX),
      conf.get('force_prefix', self.FORCE_PREFIX),
      conf.get('raw_prefix', self.RAW_PREFIX),
      conf.get('template_prefix', self.TEMPLATE_PREFIX),
      conf.get('dir_template_filename', None),
    )
    include_dirname = conf.get('include_dirname', self.INCLUDE_DIRNAME)
    pathmod_filename = conf.get('pathmod_filename', self.PATHMOD_FILENAME)
    return tempiny_l, file_name_parser, include_dirname, pathmod_filename
  
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
  def getFirstMatch(l, path):
    """
    Get the second item of the first match on the frist item in a list of couples
    """
    return next(obj for glob_pat, obj in l if path.match(glob_pat))
  
  @staticmethod
  def parseFilePath(path, file_name_parser, pathmods, is_dir=False):
    """
    @return out_name, is_opt, is_template
    """
    new_path = Path(path)
    final = False
    if pathmods :
      for mod in pathmods :
        final, new_path = mod(new_path)
        if final :
          break
    if is_dir :
      return new_path

    if not new_path :
      return False, None, None
    name, is_opt, is_template = file_name_parser.parse(path.name if final else new_path.name)
    if not final :
      new_path = new_path.with_name(name)
    return new_path, is_opt, is_template

  @staticmethod
  def parsePathMod(path, base_locals):
    if path.is_file() :
      _locals = C.fromDict(base_locals)
      with path.open('r') as f :
        obj = compile(f.read(), path, 'exec')
      exec(obj, _locals.asDict(), _locals)
      return _locals.get('pathmod')
    else:
      return None
      

  @staticmethod
  def tempinyFile(tempiny, in_f, out_f, base_locals, in_p, out_p):
    _locals = C(**base_locals)
    _locals.dest = out_p
    _locals.parent = out_p.parent if out_p is not None else None
    _locals.sls, _locals.be, _locals.ee = tempiny.conf
    template = tempiny.compile(in_f, filename=in_p)
    return template(out_f, _locals.asDict())

  @classmethod
  def processFile(cls, in_p, out_p, is_opt, is_template, base_locals, tempiny_l, dest):
    if is_template :
      tmp_out_f = OutStream()
      tempiny = cls.getFirstMatch(tempiny_l, out_p)
      with in_p.open('r') as in_f :
        _locals = {
          **base_locals,
          'beginSection' : tmp_out_f.beginSection,
          'endSection' : tmp_out_f.endSection,
          'placeholder' : tmp_out_f.placeholder,
        }
        _locals, exc = cls.tempinyFile(tempiny, in_f, tmp_out_f,  _locals, in_p, out_p)
        if exc :
          try :
            raise exc
          except EndOfPlugin:
            pass
          except ExcludeFile:
            return
      out_p = _locals.get('new_path', out_p)
      is_opt = _locals.get('is_opt', is_opt)
      if out_p is None :
        return
      out_p = dest / out_p
      if out_p.exists() :
        if is_opt :
          return
        else:
          tmp_out_f.end(out_p, _locals.get('use_sections'), _locals.get('keep_only_sections', True))
      out_p.parent.mkdir(parents=True, exist_ok=True)
      with out_p.open('w') as out_f :
        out_f.write(tmp_out_f.getvalue())
      tmp_out_f.close()
    else:
      out_p = dest / out_p
      if is_opt :
        if out_p.exists() :
          return
      shutil.copyfile(in_p, out_p)
  @staticmethod
  def processDir(base_locals, in_p, out_p, file_name_parser):
    path = in_p / file_name_parser.dir_template_filename
    if not path.exists() :
      return out_p
    with path.open('r') as f :
      obj = compile(f.read(), path, 'exec')
    _locals = C(**base_locals)
    _locals.dest = out_p
    try:
      exec(obj, _locals.asDict(), _locals)
    except EndOfPlugin:
      pass
    except ExcludeFile:
      return None
    return _locals.get('new_path', out_p)

  def execSingleFileTemplate(self, template_path : Path, dest : str, args, plugin = FlagPluginNotParsed):
    ask_help = (dest == '@help') or (args and args[0] == '--help')
    try:
      conf, plugin, help = self.parsePlugin(template_path / 'plugin.py', args, dest, ask_help)
    except PluginError as err:
      return False, err.help
    dest = Path(dest)
    
    tempiny_l, file_name_parser, include_dirname, pathmod_filename = self.parseConf(conf)
      
    base_locals = C(
      plugin=plugin,
      _p=plugin,
      C=C,
      removePrefix=file_name_parser,
      file_name_parser=file_name_parser,
      exclude=exclude,
      endOfTemplate=endOfTemplate,
    )
    base_locals.include = Include([template_path / '__include'], tempiny_l, base_locals, file_name_parser)
    
    self.processFile(template_path/'root', Path(dest.name), False, True, base_locals, tempiny_l, dest.parent)
    return True, help
    
  
  def execTemplate(self, template_path : Path, dest : str, args):
    from hl037utils.config import Config as C
    if not (template_path/'root').is_dir() :
      return self.execSingleFileTemplate(template_path, dest, args)
      
    ask_help = (dest == '@help') or (args and args[0] == '--help')
    try:
      conf, plugin, help = self.parsePlugin(template_path / 'plugin.py', args, dest, ask_help)
    except PluginError as err:
      return False, err.help
    dest = Path(dest)
    
    tempiny_l, file_name_parser, include_dirname, pathmod_filename = self.parseConf(conf)
    
    d = template_path / 'root'
    include_paths = []
    pathmod_stack = []
    base_locals = C(
      plugin=plugin,
      _p=plugin,
      C=C,
      removePrefix=file_name_parser,
      file_name_parser=file_name_parser,
      exclude=exclude,
      endOfTemplate=endOfTemplate,
    )
    base_locals.include = Include(include_paths, tempiny_l, base_locals, file_name_parser)
    
    stack = [(False, d, Path(''))]
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
      pathmod = self.parsePathMod(src / '__pathmod.py', base_locals)
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
            out_path = self.parseFilePath(out / in_p.name, file_name_parser, ( pm for pm, _ in pathmod_stack ), is_dir=True)
            out_path = self.processDir(base_locals, in_p, out_path, file_name_parser)
            if not out_path :
              continue
            stack.append((False, in_p, out_path))
          continue
          
        out_p, is_opt, is_template = self.parseFilePath(out / in_p.name, file_name_parser, ( pm for pm, _ in pathmod_stack ))
        if not out_p :
          continue
        self.processFile(in_p, out_p, is_opt, is_template, base_locals, tempiny_l, dest)    
    return True, help

  def invokeTemplate(self, template_name, dest, args):
    self.execTemplate(self.findTemplate(template_name), dest, args)

