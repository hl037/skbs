"""
Recovers the interactive-prompt experience Click had, for cyclopts:
`@promptable` lets a cyclopts command mark parameters as `Annotated[T, Prompt(...)]`
so they're interactively prompted for when omitted on the CLI, instead of
cyclopts treating them as plain required (and erroring out).

`@answer_file(path)` builds on top of that: a JSON file recording the
values used on a previous run, replayed as defaults (silently for a plain
parameter, as the suggested prompt answer for a `Prompt`-marked one) unless
overridden on the CLI, and rewritten after each successful run. Works
without `@promptable` too - every parameter is then just silently
replayed/overridden.
"""

from __future__ import annotations

import inspect
import json
from contextvars import ContextVar
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, Callable, TypeVar, get_args, get_origin, get_type_hints

import cyclopts

F = TypeVar("F", bound=Callable[..., Any])


class Prompt:
  """Marker for Annotated[] to make a missing CLI arg prompt interactively."""

  def __init__(self, message: str | None = None) -> None:
    self.message = message


def _is_multi(target_type: Any) -> bool:
  return get_origin(target_type) in (list, tuple, set, frozenset)


def _base_type(hint: Any) -> Any:
  if get_origin(hint) is Annotated:
    base_type, *_ = get_args(hint)
    return base_type
  return hint


def _stringify_one(value: Any) -> str:
  """Reverse of a single cyclopts-coerced value, back to the CLI-token
  string form (e.g. an Enum -> its .value, not its repr) - the form
  answer_file stores and re-feeds through _convert(), same as a value
  freshly typed on the CLI or at a prompt."""
  return str(value.value) if isinstance(value, Enum) else str(value)


def _to_tokens(value: Any, multi: bool) -> str | list[str]:
  return [_stringify_one(v) for v in value] if multi else _stringify_one(value)


_NO_SUGGESTION = object()

def _read_tokens(label: str, multi: bool, suggestion: Any = _NO_SUGGESTION) -> list[str]:
  """Single line for a scalar; for a list/tuple/set target, one entry per
  line until Ctrl+D (EOF), matching how the CLI itself takes one token per
  repeated flag rather than a single comma-separated string.

  `suggestion`, if given (see answer_file), is an already-coerced value
  (e.g. an Enum member, not a raw string) - shown in its CLI-token form and
  used when the answer is left empty (a blank line for a scalar, Ctrl+D
  with nothing typed for a list), same as a plain prompt with nothing
  collected, which already means "empty" absent a suggestion."""
  has_suggestion = suggestion is not _NO_SUGGESTION
  if has_suggestion:
    shown = ', '.join(_stringify_one(v) for v in suggestion) if multi else _stringify_one(suggestion)
    hint = f" [{shown}]"
  else:
    hint = ""
  if not multi:
    raw = input(f"{label}{hint}: ")
    if not raw and has_suggestion:
      return [_stringify_one(suggestion)]
    return [raw]
  print(f"{label}{hint} (one entry per line, Ctrl+D to finish):")
  tokens = []
  while True:
    try:
      raw = input("- ")
    except EOFError:
      print()
      break
    if raw.strip():
      tokens.append(raw.strip())
  if not tokens and has_suggestion:
    return [_stringify_one(v) for v in suggestion]
  return tokens


def _convert(tokens: list[str], target_type: Any) -> Any:
  """Delegate to cyclopts' own coercion engine so any token source (a CLI
  arg, a prompt answer, or a value replayed from answer_file) is parsed
  the same way (Literal, Enum, list, unions, etc.).
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


def _prompt_markers(func: Callable) -> dict[str, tuple[Prompt, Any]]:
  """Shared by promptable/answer_file: the {name: (marker, base_type)} of
  every Annotated[T, Prompt(...)] parameter with no default, keyed by name.

  Unwraps first: a parameter's "no default" signal (what marks it as
  promptable in the first place) is gone once @promptable has already
  patched it to default=None, so this always has to look at the original,
  undecorated function - relevant when answer_file wraps an
  already-@promptable-decorated one."""
  func = inspect.unwrap(func)
  sig = inspect.signature(func)
  hints = get_type_hints(func, include_extras=True)
  found = {}
  for name, param in sig.parameters.items():
    hint = hints.get(name)
    if get_origin(hint) is not Annotated:
      continue
    base_type, *extras = get_args(hint)
    marker = next((e for e in extras if isinstance(e, Prompt)), None)
    if marker is not None and param.default is inspect.Parameter.empty:
      found[name] = (marker, base_type)
  return found


# Bridge between answer_file (outer) and promptable (inner, typically) -
# suggestions to show at a prompt (already-coerced values, e.g. an Enum
# member), and where to report back what a prompt (or an already CLI-given
# value) ultimately resolved to, so answer_file can persist it. Both
# default to "not in an answer_file call" (empty dict / None), so
# promptable works standalone with no behavior change.
_answer_suggestions: ContextVar[dict] = ContextVar('skbs_answer_suggestions', default={})
_answer_collector: ContextVar[dict | None] = ContextVar('skbs_answer_collector', default=None)


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
  prompt_params = _prompt_markers(func)
  new_params = [
    param.replace(default=None) if name in prompt_params else param
    for name, param in sig.parameters.items()
  ]

  @wraps(func)
  def wrapper(*args: Any, **kwargs: Any) -> Any:
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    suggestions = _answer_suggestions.get()
    collector = _answer_collector.get()
    for name, (marker, base_type) in prompt_params.items():
      if bound.arguments.get(name) is None:
        label = marker.message or name
        multi = _is_multi(base_type)
        suggestion = suggestions[name] if name in suggestions else _NO_SUGGESTION
        while True:
          tokens = _read_tokens(label, multi, suggestion)
          try:
            bound.arguments[name] = _convert(tokens, base_type)
            break
          except ValueError as exc:
            print(exc)
      if collector is not None:
        collector[name] = bound.arguments[name]
    return func(*bound.args, **bound.kwargs)

  wrapper.__signature__ = sig.replace(parameters=new_params)
  return wrapper  # type: ignore[return-value]


def answer_file(path: str) -> Callable[[F], F]:
  """
  Decorator factory merging a JSON "answers" file (relative to the process
  cwd) with CLI-provided values for a cyclopts command - stack it as the
  outer decorator around an already-@promptable-decorated function:

      @answer_file('.skbs_answer')
      @promptable
      def main(...): ...

  Precedence: a value explicitly given on the CLI always wins. Otherwise, a
  stored answer is used - silently for a plain (non-Prompt) parameter, or
  as the suggested default at the interactive prompt for one marked
  Annotated[T, Prompt(...)] (empty input at the prompt accepts it).

  Every stored answer is a CLI-token string (or list of strings, for a
  list/tuple/set-typed parameter) - never the raw Python value - and is
  always re-parsed through the same coercion cyclopts/promptable use for a
  fresh CLI arg or prompt answer, whether it's being silently replayed or
  offered as a prompt suggestion. This also means answer_file works with a
  plain cyclopts command with no @promptable involved at all: every
  parameter is then just silently replayed/overridden, no prompting.

  After a successful call, the file is (re)written with the final merged
  values - whichever source each one came from - so later runs build on
  them.
  """
  def decorator(func: F) -> F:
    raw_func = inspect.unwrap(func)
    sig = inspect.signature(func)
    hints = get_type_hints(raw_func, include_extras=True)
    prompt_names = set(_prompt_markers(func))
    p = Path(path)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
      stored: dict = {}
      if p.is_file():
        try:
          stored = json.loads(p.read_text())
        except (ValueError, OSError):
          stored = {}

      # Decode every stored answer through the same coercion a fresh CLI
      # token or prompt answer goes through - never trust the raw JSON
      # shape to already be the parameter's real type.
      suggestions: dict[str, Any] = {}
      for name, raw in stored.items():
        if name not in sig.parameters:
          continue
        base_type = _base_type(hints.get(name))
        tokens = raw if isinstance(raw, list) else [raw]
        try:
          suggestions[name] = _convert(tokens, base_type)
        except ValueError:
          continue  # stale/incompatible value from an older run - ignore it

      bound = sig.bind_partial(*args, **kwargs)
      bound.apply_defaults()
      for name, param in sig.parameters.items():
        if name not in suggestions or name in prompt_names:
          continue
        if bound.arguments.get(name) != param.default:
          continue  # explicit CLI value - don't override
        bound.arguments[name] = suggestions[name]

      final = dict(bound.arguments)
      suggestions_token = _answer_suggestions.set(suggestions)
      collector_token = _answer_collector.set(final)
      try:
        result = func(*bound.args, **bound.kwargs)
      finally:
        _answer_collector.reset(collector_token)
        _answer_suggestions.reset(suggestions_token)

      to_store = {}
      for name, value in final.items():
        if value is None:
          continue
        base_type = _base_type(hints.get(name))
        to_store[name] = _to_tokens(value, _is_multi(base_type))
      p.write_text(json.dumps(to_store, indent=2))

      return result

    wrapper.__signature__ = sig
    return wrapper
  return decorator
