
import re
import sys


class lazyproperty:
  def __init__(self, func):
    self.func = func
  def __get__(self, instance, cls):
    if instance is None:
      return self
    else:
      value = self.func(instance)
      setattr(instance, self.func.__name__, value)
      return value

ID = r'[A-Za-z_][A-Za-z_0-9]*'
NAME = r'(?P<name>'+ID+r')'
COMMENT = r'(?://(?P<comment>.*))?'
VAL = r'(?P<val>(?:[^/]|/(?!/))*)'
TYPE = r'(?P<type>'+ID+r')'

space_re = re.compile('\s*')

class ConstantCycleError(RuntimeError):
  pass

class Constant(object):
  NAMED = 0
  INT = 1
  line_re = re.compile(r'C\s+(?:'+TYPE+'\s+)?'+NAME+r'\s*=\s*'+VAL+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  name_re = re.compile(r'\b'+ID+r'\b')
  def __init__(self, table, m):
    self.table = table
    self.m = m
    self._computing = False
    self.kind = Constant.NAMED
    
  @lazyproperty
  def name(self):
    return self.m.group('name').strip()
    
  @lazyproperty
  def val(self):
    return self.m.group('val').strip()
    
  @lazyproperty
  def comment(self):
    s = self.m.group('comment')
    if s:
      return s.strip()
    return None
  
  @lazyproperty
  def type(self):
    s = self.m.group('type')
    if s:
      return s.strip()
    return 'int'

  
  @lazyproperty
  def computed(self):
    return eval(self.computedStr)
  
  @lazyproperty
  def computedStr(self):
    if self._computing:
      raise ConstantCycleError()
    self._computing = True
    s = Constant.name_re.sub(lambda x : '(' + self.table[x.group(0)].computedStr + ')', self.val).strip()
    return "{0:#010x}".format(eval(s) & 0xffffffff)

  def __repr__(self):
    return '{} = {}  ({}) // {}'.format(self.name, self.val, self.computed, self.comment)
  
  def __str__(self):
    return repr(self)

class IntConstant(object):
  def __init__(self, val):
    self.val = val
    self.name = 'C' + str(val)
    self.comment = ''
    self.computed = val
    self.computedstr = str(val)
    self.kind = Constant.INT

class Type(object):
  def __repr__(self):
    return self.name
  def __str__(self):
    return repr(self)

class Builtin(Type):
  order = 0
  def __init__(self, name):
    self.name = name

class Array(Type):
  order = 1
  def __init__(self, t, nb):
    self.t = t
    self.nb = nb
  
  @lazyproperty
  def name(self):
    return '{}[{}]'.format(self.t.name, self.nb.val if self.nb is not None else '')

class Enum(Type):
  enum_re = re.compile(r'E\s+'+NAME+r'\s*:\s*'+TYPE+r'?\s*{\s*'+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  enum_line_re = re.compile(r'\s*'+NAME+r'\s*=\s*'+VAL+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  enum_end_re = re.compile(r'\s*}.*', re.A | re.DOTALL | re.MULTILINE)
  order = 4
  def __init__(self, Types, m):
    self.m = m
    self.constants = []
    self.Types = Types
  
  def addConstant(self, *args, **kwargs):
    self.constants.append(*args, **kwargs)
    
  @lazyproperty
  def name(self):
    return self.m.group('name').strip()

  @lazyproperty
  def type(self):
    return self.Types[self.m.group('type')]
    
  @lazyproperty
  def comment(self):
    s = self.m.group('comment')
    if s:
      return s.strip()
    return None
  
  def reprConstants(self):
    return '   ' + '\n   '.join(repr(f) for f in self.constants)

  def __repr__(self):
    return 'Enum {} : {} {{\n{}\n}}'.format(self.name, repr(self.type), self.reprConstants())
  
  def __str__(self):
    return repr(self)

class Field(object):
  struct_field_re = re.compile(r'\s*(?P<type>'+ID+r')(?P<array>(?:\s*\[(?:\d+|'+ID+r')?\])*)\s*'+NAME+r'\s*'+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  array_re = re.compile(r'\[\s*(?P<nb>[_a-zA-Z0-9]+)?\s*\]')
  comment_continuation = re.compile(r'\s*' + COMMENT, re.A | re.DOTALL | re.MULTILINE)
  def __init__(self, Constants, types, m):
    self.m = m
    self.types = types
    self.Constants = Constants
  
  @lazyproperty
  def type(self):
    t = self.types[self.m.group('type')]
    a = self.m.group('array')
    m = Field.array_re.match(a, 0)
    while m:
      nb = m.group('nb')
      if nb is None:
        c = None
      else:
        c = self.Constants.get(nb)
        if c is None:
          c = IntConstant(int(nb))
      t = Array(t, c)
      m = Field.array_re.match(a, m.end())
    return t
  
  @lazyproperty
  def name(self):
    return self.m.group('name')
  
  @lazyproperty
  def comment(self):
    s = self.m.group('comment')
    if s:
      return s.strip()
    return None
  
  def __repr__(self):
    return '{} {}; //{}'.format(repr(self.type) if self.type.order < Struct.order else self.type.name, self.name, self.comment)
  
  def __str__(self):
    return repr(self)

class Struct(Type):
  struct_re = re.compile(r'S\s+'+NAME+r'\s*{\s*'+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  struct_end_re = Enum.enum_end_re
  order = 2
  def __init__(self, m):
    self.m = m
    self.fields = []
  
  def addField(self, *args, **kwargs):
    self.fields.append(Field(*args, **kwargs))

  @lazyproperty
  def name(self):
    return self.m.group('name')

  @lazyproperty
  def pyfmt(self):
    return ''.join(x.type().pyfmt() for x in self.fields)

  def reprFields(self):
    return '   ' + '\n   '.join(repr(f) for f in self.fields)

  def __repr__(self):
    return 'Struct {} {{\n{}\n}}'.format(self.name, self.reprFields())
  
  def __str__(self):
    return repr(self)

class InvalidConstantError(RuntimeError):
  pass
    

class Packet(Struct):
  package_re = re.compile(r'(?P<direction><|>|<>)\s*'+NAME+r'\s*\(\s*(?P<type>'+ID+r')\s*\)\s*{\s*'+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  order = 3
  def __init__(self, m, Constants):
    t = m.group('type')
    self.type = Constants[t]
    super().__init__(m)
  
  @lazyproperty
  def direction(self):
    return self.m.group('direction')
  
  
  def __repr__(self):
    return 'Packet {}({}) {{\n{}\n}}'.format(self.name, self.type, self.reprFields())
  
  def __str__(self):
    return repr(self)

class Alias(Type):
  alias_re = re.compile(r'(?P<direction><|>|<>)\s*'+NAME+r'\s*=\s*(?P<alias>'+ID+')\s*\(\s*(?P<type>'+ID+r')\s*\)?\s*'+COMMENT, re.A | re.DOTALL | re.MULTILINE)
  order = 5
  def __init__(self, m, Constants, P):
    self.m = m
    aliasname = self.m.group('alias') 
    a = next((x for x in P if x.name == aliasname), None)
    if a is None:
      raise KeyError(aliasname)
    self.alias = a
    t = m.group('type')
    if t is None:
      self.type = self.alias.type
    else:
      self.type = Constants[t]
    
  @lazyproperty
  def name(self):
    return self.m.group('name')
  
  @lazyproperty
  def direction(self):
    return self.alias.direction
  
  @lazyproperty
  def comment(self):
    s = self.m.group('comment')
    if s:
      return s.strip()
    return None

  @lazyproperty
  def fields(self):
    return self.alias.fields
    
  def __repr__(self):
    return 'Alias {} = {}'.format(self.name, self.alias)
  
  def __str__(self):
    return repr(self)
  
  
    


def addFields(Consts, S, s, it):
  for l in it:
    m = Struct.struct_end_re.fullmatch(l)
    if m:
      break
    m = Field.struct_field_re.fullmatch(l)
    if not m:
      if space_re.fullmatch(l):
        continue
      m = Field.comment_continuation.fullmatch(l)
      if m:
        continue
      raise RuntimeError('Error in [ {} ]\n at line {}'.format(repr(s), l))
    s.addField(Consts, S, m)



BuiltinTypes = { n : Builtin(n) for n in (
  'int8',  'int16',  'int32',  'int64',
  'uint8', 'uint16', 'uint32', 'uint64',
  'float', 'double', 'char', 'byte'
)}

class Protocol(object):
  """
  Class to represent a protocol
  """
  def __init__(self, Constants = dict(), Structs = dict(), Packets = dict()):
    if Constants is None:
      self.Constants = dict()
    else:
      self.Constants = Constants
    if Structs is None:
      self.Structs = dict()
    else:
      self.Structs = Structs
    if Packets is None:
      self.Packets = dict()
    else:
      self.Packets = Packets
    if Types is None:
      self.Types = dict(BuiltinTypes)
    else:
      self.Types = Types

    self.C = []
    self.GC = []
    self.S = []
    self.E = []
    self.P = []

  def parse(self, f, file_name, ):
    it = iter(enumerate(f))
    try:
      for i, l in it:
        m = Constant.line_re.fullmatch(l)
        if m:
          c = Constant(self.Constants, m)
          self.Constants[c.name] = c
          self.C.append(c)
          self.GC.append(c)
        else:
          m = Enum.enum_re.fullmatch(l)
          if m:
            e = Enum(BuiltinTypes, m)
            for l in it:
              m = Enum.enum_end_re.fullmatch(l)
              if m :
                break
              m = Enum.enum_line_re.fullmatch(l)
              if m:
                c = Constant(self.Constants, m)
                self.Constants[c.name] = c
                self.C.append(c)
                e.addConstant(c)
            self.Types[e.name] = e
            self.E.append(e)
      f.seek(0)
      it = iter(enumerate(f))
      for i, l in it:
        m = Struct.struct_re.fullmatch(l)
        if m:
          s = Struct(m)
          addFields(self.Constants, self.Types, s, it)
          self.Structs[s.name] = s
          self.Types[s.name] = s
          self.S.append(s)
          continue
        m = Packet.package_re.fullmatch(l)
        if m:
          s = Packet(m, self.Constants)
          addFields(self.Constants, self.Types, s, it)
          self.Packets[s.name] = s
          self.P.append(s)
          continue
        m = Alias.alias_re.fullmatch(l)
        if m:
          s = Alias(m, self.Constants, self.P)
          self.Packets[s.name] = s
          self.P.append(s)
    except Exception as e:
      raise RuntimeError(f'{file_name}:{i} : Error while treating {l}') from e


