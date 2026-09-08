
from . import _gencontext
from .pluginutils import PluginError


def gen(template_name, dest='@', *args, out_f=None, result=None):
  """
  Generate `template_name` to `dest`.

  Outside a running template: plain entry point, equivalent to `skbs gen`.
  `dest='@'` requires `out_f` (single-file templates only). `dest=<path>`
  is resolved relative to the cwd, with no restriction.

  Inside a running template (plugin.py or a per-file template): `dest='@'`
  defaults to the calling file's own output stream if `out_f` isn't given.
  `dest=<path>` is resolved relative to the calling template's own output
  directory (or, if called from a `_template.` acting on itself, the
  directory that `_template.` governs) - escaping the current template's
  output root raises `PluginError`.

  `result`, if given, is a dict-like object (`dict`, `Config`/`C()`) that
  gets filled (via `.update(...)`) with the final locals of a generated
  single-file template - output only, never used to inject variables into
  the called template. Ignored for multi-file templates.
  """
  ctx = _gencontext.current()
  args = list(args)
  if ctx is None :
    from . import configutils
    if dest == '@' and out_f is None :
      raise ValueError("skbs.gen(dest='@') requires out_f when called outside a running template")
    backend = configutils.getBackend()
    template_path = backend.findTemplate(template_name, single_file_authorized=out_f is not None)
    return backend.execTemplate(template_path, dest, args, out_f, result=result)

  backend = ctx.backend
  if dest == '@' :
    resolved_dest, target_out_f = '@', (out_f if out_f is not None else ctx.out)
  else :
    candidate = (ctx.parent / dest).resolve()
    if not candidate.is_relative_to(ctx.root.resolve()) :
      raise PluginError(f"skbs.gen(dest={dest!r}) escapes the template's output root ({ctx.root})")
    resolved_dest, target_out_f = str(candidate), out_f
  template_path = backend.findTemplate(template_name, single_file_authorized=target_out_f is not None)
  return backend.execTemplate(template_path, resolved_dest, args, target_out_f, result=result)


class _TemplateSkbs:
  """What `skbs` refers to inside a running template - exposes only `gen`."""
  gen = staticmethod(gen)

templateSkbs = _TemplateSkbs()
