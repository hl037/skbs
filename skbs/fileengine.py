
"""
Per-file templating engine: sections/placeholders (OutStream), includes, and
walking a template's file tree to generate output.
"""

import io
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import _gencontext
from .pluginutils import (
  Config as C, EndOfPlugin, PluginError, ExcludeFile, EndOfTemplate,
  extractHelpFromLocals,
)
from .pathresolve import parseFilePath, getFirstMatch, tempinyFromIterable, FileNameParser


@dataclass
class FileGlobals:
  """
  Fixed contract of names skbs injects into per-file template execution
  (a multi-file template's `root/` tree). `plugin`/`_p` is the free-form
  object plugin.py fills in — kept opaque here, not decomposed. Built via
  `vars(this)`, same rationale as pluginloader.PluginGlobals.
  """
  plugin: C
  _p: C
  C: type
  removePrefix: Callable
  file_name_parser: FileNameParser
  exclude: Callable
  endOfTemplate: Callable
  skbs: object


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

    out_path, is_opt, is_template = parseFilePath(p, self.file_name_parser, None)

    if is_template != False :
      with p.open('r') as in_f :
        tempiny, _ = tempinyFromIterable(in_f)
      is_template = is_template or (tempiny is not None)

    if is_opt :
      raise RuntimeError("An included file can't be optionnal")
    if is_template :
      if tempiny is None :
        if out_path :
          tempiny = getFirstMatch(self.tempiny_l, out_path)
        else:
          _, tempiny = self.tempiny_l[0]
      _locals = C(**self.base_locals, **_locals)
      out = io.StringIO()
      with p.open('r') as in_f :
        _locals, exc = tempinyFile(tempiny, in_f, out, _locals, p, None)
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
    self.touched = False
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
    self.touched = True
    self.lines.extend(s.split('\n')[:-1])

  def touch(self):
    self.touched = True

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


def tempinyFile(tempiny, in_f, out_f, base_locals, in_p, out_p):
  _locals = C(**base_locals)
  # This `dest` shadows the plugin-level `dest` (the output root, see
  # pluginloader.parsePlugin): here it's the current file's path *relative
  # to that root*, and it is NOT YET joined with it (the join happens
  # later, in processFile: `out_p = dest / out_p`). Calling `.absolute()`
  # here resolves against cwd, not against the real destination root.
  _locals.dest = out_p
  _locals.parent = out_p.parent if out_p is not None else None
  _locals.sls, _locals.be, _locals.ee = tempiny.conf
  template = tempiny.compile(in_f, filename=in_p, add_to_linecache=True)
  return template(out_f, _locals.asDict())

def processFile(in_p, out_p, is_opt, is_template, base_locals, tempiny_l, dest, out_f=None, backend=None, root=None):
  tempiny = None
  if is_template != False :
    with in_p.open('r') as in_f :
      tempiny, _ = tempinyFromIterable(in_f)
    is_template = is_template or (tempiny is not None)

  if is_template :
    tmp_out_f = OutStream()
    if tempiny is None :
      if out_p :
        tempiny = getFirstMatch(tempiny_l, out_p)
      else:
        _, tempiny = tempiny_l[0]
    with in_p.open('r') as in_f :
      _locals = {
        **base_locals,
        'beginSection' : tmp_out_f.beginSection,
        'endSection' : tmp_out_f.endSection,
        'placeholder' : tmp_out_f.placeholder,
      }
      parent = (dest / out_p).parent if out_p is not None else dest
      with _gencontext.pushed(backend, root, parent, tmp_out_f):
        _locals, exc = tempinyFile(tempiny, in_f, tmp_out_f,  _locals, in_p, out_p)
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

def processDir(base_locals, in_p, out_p, file_name_parser, dest=None, backend=None):
  """
  Run `in_p`'s `_template.` file, if any, to decide where the directory
  `in_p` should end up (`new_path`), or whether it should be skipped
  entirely (`exclude()`).

  If the file has the skbs header, it's processed like a regular template
  (raw blocks, sections/placeholders, `touch()` all available) instead of
  plain Python. Whether it has the header or not, if it wrote any content
  or called `touch()` (`_OUT.touched`), `in_p` becomes a regular *file*
  with that content instead of a directory - none of its own children are
  processed in that case.

  @return (new_path, content) - content is None unless `in_p` should become a file.
  """
  path = in_p / file_name_parser.dir_template_filename
  if not path.exists() :
    return out_p, None
  with path.open('r') as f :
    tempiny, _ = tempinyFromIterable(f)
  _locals = C(**base_locals)
  _locals.dest = out_p
  tmp_out_f = OutStream()
  root = Path(dest).resolve() if dest is not None else None
  parent = (dest / out_p) if (dest is not None and out_p is not None) else dest
  try:
    with _gencontext.pushed(backend, root, parent, tmp_out_f):
      if tempiny is not None :
        with path.open('r') as f :
          _locals_dict = {
            **_locals.asDict(),
            'beginSection' : tmp_out_f.beginSection,
            'endSection' : tmp_out_f.endSection,
            'placeholder' : tmp_out_f.placeholder,
            'touch' : tmp_out_f.touch,
          }
          _locals, exc = tempinyFile(tempiny, f, tmp_out_f, _locals_dict, path, out_p)
          if exc :
            raise exc
      else :
        with path.open('r') as f :
          obj = compile(f.read(), path, 'exec')
        _locals.touch = tmp_out_f.touch
        exec(obj, _locals.asDict(), _locals)
  except EndOfTemplate:
    pass
  except ExcludeFile:
    return None, None
  content = tmp_out_f.getvalue() if tmp_out_f.touched else None
  return _locals.get('new_path', out_p), content

def parsePathMod(path, base_locals):
  if path.is_file() :
    _locals = C.fromDict(base_locals)
    with path.open('r') as f :
      obj = compile(f.read(), path, 'exec')
    exec(obj, _locals.asDict(), _locals)
    return _locals.get('pathmod')
  else:
    return None
