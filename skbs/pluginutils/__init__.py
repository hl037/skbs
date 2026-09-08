
import io

# EndOfPlugin, EndOfTemplate, ExcludeFile and PluginError are skbs's internal
# control-flow signals (used in place of `return`/`continue` across the
# plugin.py / per-file template boundary, see backend.py). Template authors
# aren't meant to catch or raise these classes directly in general: the
# public surface is the exclude()/endOfTemplate()/pluginError() functions
# below. The exception: EndOfPlugin and PluginError are also handed directly
# to plugin.py's namespace (see Backend.parsePlugin) so that
# `raise EndOfPlugin()` / `raise PluginError(help)` work there too — kept for
# backward compatibility with existing templates (e.g. the default one).
class EndOfPlugin(Exception):
  pass

class EndOfTemplate(Exception):
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

class _MissingClick:
  """
  Stands in for the `click` module in a template's namespace when click
  isn't installed (it's optional, see pyproject.toml's `click` extra).
  Any use (`click.command(...)`, `click.Context(...)`, etc.) raises a
  PluginError with install instructions instead of skbs itself failing to
  import, or the template failing with a confusing AttributeError/TypeError.
  """
  def __getattr__(self, name):
    def _raise(*args, **kwargs):
      raise PluginError(
        'This template uses `click`, which is not installed.\n'
        'Install it with: pip install skbs[click]'
      )
    return _raise

def getClick():
  try:
    import click
    return click
  except ImportError:
    return _MissingClick()

class ExcludeFile(Exception):
  pass

def exclude():
  raise ExcludeFile()

def endOfTemplate():
  raise EndOfTemplate()

def endOfPlugin():
  raise EndOfPlugin()

def extractHelpFromLocals(loc):
  """
  Used by both plugin loading and per-file template processing to recover
  the help message a plugin/template exposed (via `__doc__` or `help`).
  """
  return next(( h for k in ('__doc__', 'help') if (h := loc.get(k)) ), 'No help provided for this template' )


__name = '--'

def invokeCmd(cmd, args, **extra):
  """
  Invoke a click command. `__name` (settable by the caller, e.g. skbs's own
  CLI) is used as the command's displayed name, so its usage string can
  read as if it were nested under the invoking command
  (e.g. "skbs gen mytemplate dest --") without needing a real click.Context
  to chain to.
  **extra are passed to cmd.make_context
  """
  from click.exceptions import Exit, ClickException
  from .._internal_click_monkey_patches import __get_help_option, silentClick
  stderr = io.StringIO()
  with silentClick(stderr):
    try :
      ctx = cmd.make_context(__name, args, **extra)
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

def invokeCmdCyclopts(app, args):
  """
  Invoke a cyclopts.App, capturing its output the same way invokeCmd does
  for a click.Command: any output (help text, an error, or the command's
  own prints) becomes a PluginError; silence means success.
  """
  import contextlib
  buf = io.StringIO()
  with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    try :
      app(args)
    except SystemExit :
      pass
  out = buf.getvalue()
  if out :
    raise PluginError(out)

class OptionParser(object):
  """
  Use invokeCmd to parse options and put the result in a dict-like.
  """
  def __init__(self, args:list[str], opts:'Config'):
    self.args = args
    self.opts = opts

  def __call__(self, *click_opts):
    @getClick().command(name='')
    def cmd(**kwargs):
      self.opts.update(kwargs)
    for opt in click_opts :
      cmd = opt(cmd)
    invokeCmd(cmd, self.args)
    return self.opts
  
class _Default:
  pass
class Config(object):
  """
  Dict-like, attribute-accessible bag of values (`C(x=1).x == 1`), aliased
  as `C` throughout skbs. Used both for the fixed, framework-injected
  namespace of plugin.py/per-file templates, and as the free-form `plugin`/
  `_p` object template authors extend with arbitrary attributes.
  """
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
  def register(self, obj):
    self.__d__[obj.__name__] = obj
    return obj
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


