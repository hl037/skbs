
"""
Path/filename resolution and template discovery: pure functions and classes,
no dependency on Backend.
"""

import re
from pathlib import Path
from itertools import chain

from tempiny import Tempiny

OPT_PREFIX = '_opt.'
TEMPLATE_PREFIX = '_template.'
FORCE_PREFIX = '_force.'
RAW_PREFIX = '_raw.'
INCLUDE_DIRNAME = '__include'
PATHMOD_FILENAME = '__pathmod.py'

tempinySyntaxRegex = re.compile(r'^(\s*\S+)\s+\#\s+(\S+)__skbs_template__(\S+)\s*$')

def tempinyFromLine(l):
  m = tempinySyntaxRegex.fullmatch(l)
  if not m :
    return None
  return Tempiny(stmt_line_start=m[1], begin_expr=m[2], end_expr=m[3])

def tempinyFromIterable(iterable):
  # New version support template file describing themselves their syntax...
  it = iter(iterable)
  try :
    first_line = next(it)
  except :
    return None, tuple()
  new_it = chain((first_line,), it)
  return tempinyFromLine(first_line), new_it

def _get(d, k, default):
  v = d.get(k, None)
  if v is None :
    return default, False
  return v, True

def isTemplate(p: Path, sft=False):
  if p.is_dir() :
    return (p / 'root').exists()
  elif sft :
    return p.exists()
  try :
    with open(p, 'r') as f :
      l = f.readline()
    if tempinySyntaxRegex.match(l) :
      return True
  except :
    pass
  return False

def _findTemplates(d: Path, root: Path, rec=True, dirs=False, sft=False) -> str:
  now = []
  after = []
  try :
    for c in (root / d).iterdir() :
      if isTemplate(c, sft) :
        now.append(str(c.relative_to(root)))
      elif (c).is_dir() :
        after.append(c.relative_to(root))
  except :
    pass
  yield from sorted(now)
  if rec :
    for c in sorted(after) :
      yield from _findTemplates(c, root, rec, dirs, sft)
  if dirs :
    yield from ( f'{p}/' for p in after )

def findTemplates(d: Path, root: Path, rec=True, dirs=False, sft=False) -> str:
  if isTemplate(root / d, sft) :
    yield str(d)
  else :
    yield from _findTemplates(d, root, rec, dirs, sft)

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
        self.dir_template_filename = TEMPLATE_PREFIX


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

def getFirstMatch(l, path):
  """
  Get the second item of the first match on the first item in a list of couples
  """
  return next(obj for glob_pat, obj in l if path.match(glob_pat))

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
