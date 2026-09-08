
"""
Context stack tracking "am I currently running inside a template, and if
so with which backend/root/parent/output stream" - the only state
skbs.gen() needs to decide how to resolve `dest` and where to send output.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GenContext:
  backend: object    # Backend instance currently in use (same config/template dirs)
  root: Path          # absolute output root of the current top-level template - the anti-traversal boundary
  parent: Path         # absolute directory used to resolve a relative dest (differs for _template. vs a regular file)
  out: object | None    # current OutStream (_OUT), used as out_f default when dest='@' and none given

_current = ContextVar('skbs_gen_context', default=None)

@contextmanager
def pushed(backend, root, parent, out):
  token = _current.set(GenContext(backend, root, parent, out))
  try:
    yield
  finally:
    _current.reset(token)

def current():
  return _current.get()
