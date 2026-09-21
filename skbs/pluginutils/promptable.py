"""
Recovers the interactive-prompt experience Click had, for cyclopts:
`@promptable` lets a cyclopts command mark parameters as `Annotated[T, Prompt(...)]`
so they're interactively prompted for when omitted on the CLI, instead of
cyclopts treating them as plain required (and erroring out).
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Annotated, Any, Callable, TypeVar, get_args, get_origin, get_type_hints

import cyclopts

F = TypeVar("F", bound=Callable[..., Any])


class Prompt:
  """Marker for Annotated[] to make a missing CLI arg prompt interactively."""

  def __init__(self, message: str | None = None) -> None:
    self.message = message


def _is_multi(target_type: Any) -> bool:
  return get_origin(target_type) in (list, tuple, set, frozenset)


def _read_tokens(label: str, multi: bool) -> list[str]:
  """Single line for a scalar; for a list/tuple/set target, one entry per
  line until Ctrl+D (EOF), matching how the CLI itself takes one token per
  repeated flag rather than a single comma-separated string."""
  if not multi:
    return [input(f"{label}: ")]
  print(f"{label} (one entry per line, Ctrl+D to finish):")
  tokens = []
  while True:
    try:
      raw = input("- ")
    except EOFError:
      print()
      break
    if raw.strip():
      tokens.append(raw.strip())
  return tokens


def _convert(tokens: list[str], target_type: Any) -> Any:
  """Delegate to cyclopts' own coercion engine so prompt input is parsed
  the same way CLI tokens would be (Literal, Enum, list, unions, etc.).
  An empty token list for a list/tuple/set target (Ctrl+D with no entries
  typed) is special-cased to an empty collection: cyclopts.convert(..., [])
  raises a bare, message-less ValueError for these instead of accepting it,
  which would otherwise silently loop the prompt with no visible feedback."""
  if not tokens and _is_multi(target_type):
    return get_origin(target_type)()
  try:
    return cyclopts.convert(target_type, tokens)
  except (cyclopts.CoercionError, ValueError):
    # cyclopts.CoercionError.__str__ can itself raise when used outside a
    # full binding context, so we deliberately drop the original traceback.
    raise ValueError(f"invalid value {tokens!r} for {target_type}") from None


def promptable(func: F) -> F:
  """Allow parameters marked with Annotated[T, Prompt(...)] to be omitted on
  the CLI (positional or keyword) and interactively prompted for at call time.

  The wrapped function keeps its original (non-Optional) signature; only the
  signature exposed to cyclopts is patched with default=None on those params.

  Note: since Prompt params get default=None, a positional Prompt param
  followed by a positional required (non-Prompt) param raises a standard
  Python "non-default argument follows default argument" error. Put required
  positional params before Prompt ones, or make Prompt params keyword-only.
  """
  sig = inspect.signature(func)
  hints = get_type_hints(func, include_extras=True)

  prompt_params: dict[str, tuple[Prompt, Any]] = {}
  new_params = []
  for name, param in sig.parameters.items():
    hint = hints.get(name)
    marker = None
    base_type = hint
    if get_origin(hint) is Annotated:
      base_type, *extras = get_args(hint)
      marker = next((e for e in extras if isinstance(e, Prompt)), None)
    if marker is not None and param.default is inspect.Parameter.empty:
      prompt_params[name] = (marker, base_type)
      param = param.replace(default=None)
    new_params.append(param)

  @wraps(func)
  def wrapper(*args: Any, **kwargs: Any) -> Any:
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    for name, (marker, base_type) in prompt_params.items():
      if bound.arguments.get(name) is None:
        label = marker.message or name
        multi = _is_multi(base_type)
        while True:
          tokens = _read_tokens(label, multi)
          try:
            bound.arguments[name] = _convert(tokens, base_type)
            break
          except ValueError as exc:
            print(exc)
    return func(*bound.args, **bound.kwargs)

  wrapper.__signature__ = sig.replace(parameters=new_params)
  return wrapper  # type: ignore[return-value]
