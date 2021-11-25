
import io
import json
import linecache
import os
import pkg_resources
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
from itertools import accumulate, chain
from traceback import print_exc

from tempiny import Tempiny
from .pluginutils import Config as C, EndOfPlugin, PluginError, ExcludeFile, exclude, pluginError, EndOfTemplate, endOfTemplate, invokeCmd, OptionParser

import click



sys.excepthook = print_exc

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
    
    if is_template != False :
      with p.open('r') as in_f :
        tempiny, _ = tempinyFromIterable(in_f)
      is_template = is_template or (tempiny is not None)

    if is_opt :
      raise RuntimeError("An included file can't be optionnal")
    if is_template :
      if tempiny is None :
        if out_path :
          tempiny = Backend.getFirstMatch(self.tempiny_l, out_path)
        else:
          _, tempiny = self.tempiny_l[0]
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
    # Since the included content could be in the middle of a line, the extra '\n' should be removed
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
      self.dir_template_filename = template_prefix[0]
      if self.dir_template_filename is None :
        self.dir_template_filename = Backend.TEMPLATE_PREFIX
        

  def parse(self, name:str):
    """
    Formula is as follow : 
    O : opt prefix is defined
    F : force prefix is defined
    R : raw prefix is defined
    T : template prefix is defined

    o : opt prefex is present in filename
    f : force prefex is present in filename
    r : raw prefex is present in filename
    t : template prefex is present in filename

    h : a synheader line is present at file start
    d : is_opt is defined
    v : value of not is_opt

    is_template = !r.t + t.!R.T + !r.R.!T + h(r.t.!R.!T + !r.!t.!R.!T + !r.!t.R.T)
    
    D = d.is_template

    force = D.v + !D(!o.f + !o.F + f.!O + !o.O)

    is_opt = !force

    This function returns (name, _is_opt, _is_template)
    where :

    name : name with prefixed removed
    _is_opt = !(!o.f + !o.F + f.!O + !o.O)
    _is_template = {True if !r.t + t.!R.T + !r.R.!T ; False if !(!r.t + t.!R.T + !r.R.!T).!(r.t.!R.!T + !r.!t.!R.!T + !r.!t.R.T); None else }

    """
    Opre, O = self.opt_prefix
    Fpre, F = self.force_prefix
    Rpre, R = self.raw_prefix
    Tpre, T = self.template_prefix
    
    o = False
    if name.startswith(Opre) :
      o = True
      name = name[len(Opre):]
      
    f = False
    if name.startswith(Fpre) :
      f = True
      name = name[len(Fpre):]
      
    r = False
    if name.startswith(Rpre) :
      r = True
      name = name[len(Rpre):]
      
    t = False
    if name.startswith(Tpre) :
      t = True
      name = name[len(Tpre):]

    Ea = t and ( not r or r and not R and T ) or not r and R and not T
    Eb = (
          r and     t and not R and not T or
      not r and not t and ( not R and not T or R and T )
    )

    Ec = f and not O or not o and ( f or not F or O)

    return name, not Ec, True if Ea else False if not Ea and not Eb else None
    
  
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

  class MatchWithZeroLines(RuntimeError):
    pass

  @staticmethod
  def matcher(m_lines, offset=0):
    def match(lines, i):
      i += offset
      return lines[i:i+len(m_lines)] == m_lines
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
    def __init__(self, name, cb, begin_line):
      self.name = name
      self.cb = cb
      self.begin_line = begin_line
      self.ori_end_line = begin_line
      self.ori_begin_line = None
      self.ori_end_line = None
      self.sections = []
      self.begin = cb
      self.end = lambda *args, **kwargs:True

    def __repr__(self):
      return f'Placeholder(name={self.name}, cb={self.cb}, bl={self.begin_line}, o_bl={self.ori_begin_line}, n_sec={len(self.sections)})'
      
  def __init__(self):
    self.lines = []
    self.sections = []
    self.cur_section = None
    self._placeholders = []
    self.placeholders = []

  def beginSection(self, m=0, n=1, cb=None, placeholder=None, overwrite=None):
    """
    Start an overwritten section.
    
    @param cb : A calback function ``cb(lines, i)`` where ``lines`` is a list of the lines in the original file, and ``i`` is the index of the current line being checked. The function should return true if lines[i] is the first line inside the section.
    @param n
    @param m : If ``cb`` is None, Then the section begin will try to match ``lines[cur + m : cur + n]`` in both the virtual output template and the original file.
    @param placeholder If a placeholder is specified and the original file does not have this section, then it will be put just before the placeholder (so that further added sections go always to the end)
    @param overwrite : is True, use the content from the tempalte's virtual output, else, use the content of the original file.
If left unset or ``None``, will have ``not keep_only_sections`` as value to get an intuitive behavior
It can also be to a callable object with this signature : ``overwrite(original: list[str], virtual: list[str], ctx: Callable[[], 'Context']) -> list[str]``. Where ``origninal`` and ``virtual`` are respectively the content of the matched section. ctx is a callable to obtain the context, it returns an object with the follwing attributes read-only:

 * ``o`` : Original file :
    * ``o.lines`` : original file lines
    * ``o.sec_b`` : begin of section
    * ``o.sec_e`` : end of section
 * ``v`` Virtual output :
    * ``o.lines`` : original file lines
    * ``o.sec_b`` : begin of section
    * ``o.sec_e`` : end of section
 * ``keep_only_sections``
    """
    if m == n :
      raise self.MatchWithZeroLines('A placeholder was create with n == 0')
    if self.cur_section is not None :
      raise OutStream.AlreadyInSectionError("Sections cannot be nested")
    self.cur_section = OutStream.Section(placeholder, overwrite), len(self.lines), m, n, cb


  def endSection(self, m=-1, n=0, cb=None):
    """
    End an overwritten section.
    
    @param cb : ``cb`` is a calback function ``cb(lines, i)`` where ``lines`` is a list of the lines in the original file, and ``i`` is the index of the current line being checked. The function should return true if lines[i] is the last line (inclusive) inside the section.
    @param n
    @param m : If ``cb`` is None, Then the section end will try to match ``lines[cur + m : cur + n]`` in both the virtual output template and the original file.
    """
    if m == n :
      raise self.MatchWithZeroLines('A placeholder was create with n == 0')
    section, i, b_m, b_n, cb_begin = self.cur_section
    end = len(self.lines)
    if cb_begin is None :
      cb_begin = self.matcher(self.lines[i + b_m : i + b_n], offset=b_m)
    if cb is None :
      cb = self.matcher(self.lines[end + m : end + n], offset=m)
    section.begin = cb_begin
    section.end = cb
    section.begin_line = i
    section.end_line = end
    self.cur_section = None
    self.sections.append(section)
  
  def placeholder(self, name, m=-1, n=0, cb=None):
    """
    Defines a placeholder
    
    @param name : name of the placeholder
    @param cb : ``cb`` is a calback function ``cb(lines, i)`` where ``lines`` is a list of the lines in the original file, and ``i`` is the index of the current line being checked. The function should return true if the section should be inserted between lines[i] and lines[i+1]

    @param n
    @param m : If ``cb`` is None, Then the placeholder will try to match ``lines[cur + m : cur + n]`` in both the virtual output template and the original file.
    """
    if m == n :
      raise self.MatchWithZeroLines('A placeholder was create with n == 0')
    if self.cur_section is not None :
      raise OutStream.AlreadyInSectionError("A placeholder cannot be placed inside a section")
    self.sections.append((name, len(self.lines), m, n, cb))
  
  def write(self, s):
    self.lines.extend(s.split('\n')[:-1])
  
  def getvalue(self):
    return "\n".join(self.lines) + '\n'

  def newPlacehoder(self, name, i, m, n, cb, /, keep_only_sections):
    return self.Placeholder(name, cb if cb else self.matcher(self.lines[i + m : i + n], m), i)

  class ContextFactory(object):
    """
    Used to provide the `ctx()` callback to overwrite callbacks
    """
    def __init__(self, orig, virt, keep_only_sections):
      self.orig = orig
      self.virt = virt
      self.section = None
      self.keep_only_sections = keep_only_sections

    def ctx(self):
      return C(
        o=C(
          lines = self.orig,
          sec_b = self.section.ori_begin_line,
          sec_e = self.section.ori_end_line,
        ),
        v=C(
          lines = self.virt,
          sec_b = self.section.begin_line,
          sec_e = self.section.end_line,
        ),
        keep_only_sections=self.keep_only_sections,
      )
  
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
    
    if keep_only_sections :
      candidate_sections = [ s for s in self.sections if isinstance(s, self.Section) ]
    else :
      candidate_sections = [ s if isinstance(s, self.Section) else self.newPlacehoder(*s, keep_only_sections=keep_only_sections) for s in self.sections ]
    
    sections = []
    # match sections in any order
    i = 0
    while i < len(lines) :
      it = iter(
          (j, s) for j, s in enumerate(candidate_sections) if s.begin(lines, i)
      )
      j, s = next(it, (None, None))
      while j is not None :
        s.ori_begin_line = i
        for i2 in range(i, len(lines) + 1) :
          if s.end(lines, i2) :
            s.ori_end_line = i2
            sections.append(s)
            candidate_sections.pop(j)
            i = i2
            break
        else :
          # The section did not end... Try next the one
          j, s = next(it, (None, None))
          continue
        break
      else :
        # We tried all the sections without success... step.
        i += 1

    # Remaining sections are the one not matched
    pldict = { pl.name : pl for pl in sections if isinstance(pl, self.Placeholder) }

    contextFactory = self.ContextFactory(lines, self.lines, keep_only_sections)
    ctx = contextFactory.ctx
    
    if keep_only_sections :
      # Replace sections in template with original file ones, except if overwrite
      for s in reversed(sections) :
        if callable(s.overwrite) :
          contextFactory.section = s
          self.lines[s.begin_line:s.end_line] = s.overwrite(
            lines[s.ori_begin_line:s.ori_end_line],
            self.lines[s.begin_line:s.end_line],
            ctx
          )
        elif s.overwrite != True : # Could be None
          self.lines[s.begin_line:s.end_line] = lines[s.ori_begin_line:s.ori_end_line]
    else:
      # Merge placeholders and sections
      # elements = sorted(chain(pldict.values(), sections), key=lambda x : x.ori_begin_line, reverse=True)
      # Place not matched sections in their placeholder
      for s in ( s for s in candidate_sections if isinstance(s, self.Section) ):
        pl = pldict.get(s.placeholder)
        if pl is not None :
          pl.sections.append(s)
          
      # Replace sections in original file with template ones except if overwrite False (in this case, only add at placeholder if not present)
      for e in reversed(sections) :
        if isinstance(e, self.Section) :
          s = e
          if callable(s.overwrite) :
            contextFactory.section = s
            lines[s.ori_begin_line:s.ori_end_line] = s.overwrite(
              lines[s.ori_begin_line:s.ori_end_line],
              self.lines[s.begin_line:s.end_line],
              ctx
            )
          elif s.overwrite != False : # Could be None
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

def extractHelpFromLocals(loc):
  return next(( h for k in ('__doc__', 'help') if (h := loc.get(k)) ), 'No help provided for this template' ) 
  

def findTemplates(d: Path, root: Path):
  if (d / 'root').exists() :
    yield d.relative_to(root)
  else :
    for c in d.iterdir() :
      if c.is_dir() :
        yield from findTemplates(c, root)
      else :
        yield c.relative_to(root)
      
tempinySyntaxRegex = re.compile(r'^(\s*\S+)\s+\#\s+(\S+)__skbs_template__(\S+)\s*$')

def tempinyFromLine(l):
  m = tempinySyntaxRegex.fullmatch(l)
  if not m :
    return None
  return Tempiny(stmt_line_start=m[1], begin_expr=m[2], end_expr=m[3])

def tempinyFromIterable(iterable):
  # New version support template file describing themselves their syntax...
  it = iter(iterable)
  first_line = next(it)
  new_it = chain((first_line,), it)
  return tempinyFromLine(first_line), new_it

def _get(d, k, default):
  v = d.get(k, None)
  if v is None :
    return default, False
  return v, True
  

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
      list(findTemplates(default_dir, default_dir)) if default_dir.is_dir() else [],
      list(findTemplates(user_dir, user_dir)) if user_dir.is_dir() else []
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

  def createDummyPluginModule(self, path, g):
    path = path.parent
    g.__package__ = '__skbs_plugin__' + str(path).replace('/', '_').replace('.','_')
    m = C(
      __name__ = g.__package__,
      __path__ = [str(path)],
      __package__ = '',
    )
    sys.modules[g.__package__] = m

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
      parseCmd=OptionParser(args, plugin),
    )
    if path.is_file() :
      # source plugin.py if one
      with path.open('r') as f :
        obj = compile(f.read(), path, 'exec')
      self.createDummyPluginModule(path, g)
      try:
        exec(obj, g.asDict(), g)
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

  def parseConf(self, conf):
    tempiny_l = None
    
    if conf is None :
      conf = C()
    if 'tempiny' in conf :
      tempiny_l = [ (pattern, Tempiny(**c)) for pattern, c in conf.tempiny ]
    else:
      tempiny_l = [ ('*', Tempiny()) ]
    
    file_name_parser = FileNameParser(
      _get(conf, 'opt_prefix', self.OPT_PREFIX),
      _get(conf, 'force_prefix', self.FORCE_PREFIX),
      _get(conf, 'raw_prefix', self.RAW_PREFIX),
      _get(conf, 'template_prefix', self.TEMPLATE_PREFIX),
      conf.get('dir_template_filename', None),
    )
    include_dirname = conf.get('include_dirname', self.INCLUDE_DIRNAME)
    pathmod_filename = conf.get('pathmod_filename', self.PATHMOD_FILENAME)
    return tempiny_l, file_name_parser, include_dirname, pathmod_filename
  
  def findTemplate(self, template, single_file_authorized=False):
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
    if single_file_authorized and p.is_file() :
      return p
    if not p.is_dir() :
      if not p.is_file() :
        raise FileNotFoundError(p)
      return p
    return p

  @staticmethod
  def getFirstMatch(l, path):
    """
    Get the second item of the first match on the first item in a list of couples
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
    template = tempiny.compile(in_f, filename=in_p, add_to_linecache=True)
    return template(out_f, _locals.asDict())

  @classmethod
  def processFile(cls, in_p, out_p, is_opt, is_template, base_locals, tempiny_l, dest, out_f=None):
    tempiny = None
    if is_template != False :
      with in_p.open('r') as in_f :
        tempiny, _ = tempinyFromIterable(in_f)
      is_template = is_template or (tempiny is not None)

    if is_template :
      tmp_out_f = OutStream()
      if tempiny is None :
        if out_p :
          tempiny = cls.getFirstMatch(tempiny_l, out_p)
        else:
          _, tempiny = tempiny_l[0]
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
          except EndOfTemplate:
            pass
          except EndOfPlugin:
            raise PluginError(extractHelpFromLocals(_locals))
          except ExcludeFile:
            return _locals
      out_p = _locals.get('new_path', out_p)
      is_opt = _locals.get('is_opt', is_opt)
      if out_p is None :
        if out_f :
          out_f.write(tmp_out_f.getvalue())
        return _locals
      out_p = dest / out_p
      if out_p.exists() :
        if is_opt :
          return _locals
        else:
          tmp_out_f.end(out_p, _locals.get('use_sections'), _locals.get('keep_only_sections', False))
      out_p.parent.mkdir(parents=True, exist_ok=True)
      if out_f :
        out_f.write(tmp_out_f.getvalue())
      else:
        with out_p.open('w') as out_f :
          out_f.write(tmp_out_f.getvalue())
      tmp_out_f.close()
      return _locals
    else:
      out_p = dest / out_p
      if is_opt :
        if out_p.exists() :
          return C()
      shutil.copyfile(in_p, out_p)
      return C()
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
    except EndOfTemplate:
      pass
    except ExcludeFile:
      return None
    return _locals.get('new_path', out_p)

  def execSingleFileTemplate(self, template_path : Path, dest : str, args:list[str], out_f=None, plugin = C()):
    ask_help = (dest == '@help') or (args and args[0] == '--help')
    if dest == '@' :
      dest_name = None
      dest_parent = Path()
    else:
      dest = Path(dest)
      dest_name = Path(dest.name)
      dest_parent = dest.parent

    # Template as file
    if template_path.is_file() :
      import re
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
        
      tempiny_l, file_name_parser, include_dirname, pathmod_filename = self.parseConf(conf)
        
      base_locals = C(
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
      )
      
      try:
        _locals = self.processFile(template_path, dest_name, False, True, base_locals, tempiny_l, dest_parent, out_f=out_f)
      except PluginError as err:
        return False, err.help
      return True, _locals.get('help')
      
    # Template as dir
    else:
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
        invokeTemplate=self.invokeTemplate,
      )
      base_locals.include = Include([template_path / '__include'], tempiny_l, base_locals, file_name_parser)
      
      self.processFile(template_path/'root', dest_name, False, True, base_locals, tempiny_l, dest_parent, out_f=out_f)
      return True, help
    
  
  def execTemplate(self, template_path : Path, dest : str, args, out_f=None):
    if not (template_path/'root').is_dir() :
      return self.execSingleFileTemplate(template_path, dest, args, out_f=out_f)
      
    if dest == '@' or out_f is not None:
      return False, 'Stream output is not available as dest for multi-file plugins.'
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
      invokeTemplate=self.invokeTemplate,
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

  def invokeTemplate(self, template_name, dest, args, out_f=None, single_file_authorized=None):
    if single_file_authorized is None :
      single_file_authorized = out_f is not None
    return self.execTemplate(self.findTemplate(template_name, single_file_authorized=single_file_authorized), dest, args, out_f)

