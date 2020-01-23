
import io
import click
from click.exceptions import Exit, Abort, ClickException
from contextlib import contextmanager
from ._internal_click_monkey_patches import CliError

from dbug import *

class EndOfPlugin(Exception):
  pass

class EndOfTemplate(EndOfPlugin):
  pass

class IsNotAModuleOrScriptError(Exception):
  def __init__(self):
    super('This file is not a module or a script. It is an skbs plugin. It should only be used through skbs.')

class PluginError(Exception):
  """
  Used to dignal an error when executing the plugin.
  To be Instanciated passing the help string.
  """
  def __init__(self, help):
    super()
    self.help = help

def pluginError(help):
  raise PluginError(help)

class ExcludeFile(Exception):
  pass

def exclude():
  raise ExcludeFile()

def endOfTemplate():
  raise EndOfTemplate()

def endOfPlugin():
  raise EndOfPlugin()


__ctx = None
__name = '--'

def invokeCmd(cmd, args, **extra):
  """
  Invoke a click command, so that the usage will be adapted to fit the parent command if one.
  **extra are passed to cmd.make_context
  """
  from ._internal_click_monkey_patches import __get_help_option, silentClick
  stderr = io.StringIO()
  with silentClick(stderr):
    try :
      ctx = cmd.make_context(__name, args, parent = __ctx, **extra)
      cmd.invoke(ctx)
    except Exit : 
      pass
    except ClickException as exc : 
      exc.show(file=stderr)
    except Exception :
      import pdb; pdb.xpm()
      raise PluginError(ctx.get_help())
  err = stderr.getvalue()
  if err :
    raise PluginError(err)
  
class _Default:
  pass
class Config(object):
  def __init__(self, **kwargs):
    self.__dict__['__d__'] = kwargs
  def keys(self):
    return self.__d__.keys()
  def values(self):
    return self.__d__.values()
  def items(self):
    return self.__d__.items()
  def get(self, k, default = None):
    return self.__d__.get(k, default)
  def getOrSetDefault(self, k, default = None):
    p = self.__d__.get(k, _Default)
    if p is _Default :
      self.__d__[k] = default
      p = default
    return p
  def update(self, d):
    return self.__d__.update(d)
  def asDict(self):
    return self.__dict__['__d__']
  def __getattr__(self, *args, **kwargs):
    try:
      return self.__d__.__getitem__(*args, **kwargs)
    except Exception as e:
      raise AttributeError(e) from e
  def __setattr__(self, *args, **kwargs):
    return self.__d__.__setitem__(*args, **kwargs)
  def __getitem__(self, *args, **kwargs):
    try:
      return self.__d__.__getitem__(*args, **kwargs)
    except Exception as e:
      raise KeyError(e) from e
  def __setitem__(self, *args, **kwargs):
    return self.__d__.__setitem__(*args, **kwargs)
  def __contains__(self, k):
    return k in self.__d__
  def __len__(self):
    return len(self.__dict__['__d__'])
  def __repr__(self):
    return repr(self.__dict__['__d__'])
  __str__ = __repr__
  @classmethod
  def fromDictRec(cls, __d__):
    if hasattr(__d__, 'items'):
      c = Config()
      c.__dict__['__d__'].update({k : cls.fromDictRec(v) for k, v in __d__.items()})
      return c
    elif isinstance(__d__, list) :
      return [ cls.fromDictRec(v) for v in __d__ ]
    else:
      return __d__
  @classmethod
  def fromDict(cls, __d__):
    c = Config()
    c.__dict__['__d__'].update(__d__)
    return c

