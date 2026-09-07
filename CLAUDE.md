# skbs

SKeleton BootStrap: a template-engine CLI (`skbs gen`). Written over 10 years ago (originally Python ~3.6), migrated to Python 3.14 + `pyproject.toml`.

## Module layout

`backend.py` used to be a ~1000-line monolith; it's now split by responsibility:

- `pathresolve.py` — pure path/filename resolution and template discovery (`findTemplates`, `FileNameParser`, `parseFilePath`, prefix constants). No dependency on `Backend`.
- `pluginloader.py` — loading a template's `plugin.py` and parsing its `conf` (`createPluginModule`, `parsePlugin`, `parseConf`, `PluginGlobals` dataclass).
- `fileengine.py` — per-file templating engine: sections/placeholders (`OutStream`), `Include`, walking a template's file tree (`processFile`, `processDir`, `parsePathMod`, `FileGlobals` dataclass).
- `backend.py` — the `Backend` orchestrator, importing from the three modules above. Also defines `SingleFileGlobals` (the flat single-file template contract).

Dependency direction is one-way: `pathresolve` → `fileengine`/`pluginloader` → `backend`. No cycles.

## The two `dest` gotcha

There are two unrelated things both called `dest`, and confusing them gives a *silently wrong* path (not a crash):

- **Plugin-level `dest`** (in `plugin.py`, via `pluginloader.parsePlugin`): the root output directory as given on the CLI. Never resolved to an absolute path by skbs — it's whatever the user typed, so it can be relative to whatever the process's cwd was.
- **Per-file `dest`** (inside a file being generated, set in `fileengine.tempinyFile`): the current file's path *relative to that root*, and NOT YET joined with it at that point (`fileengine.processFile` does `out_p = dest / out_p` only after tempinyFile returns).

Calling `.absolute()` on the per-file `dest` resolves against cwd, not against the real destination root — that's a bug waiting to happen, not a skbs limitation to work around.

**Pattern to expose the real root inside per-file templates**: in `plugin.py`, copy it onto the free-form `plugin`/`_p` object, e.g. `plugin.dest = dest.resolve()` (see `skbs/default/templates/skbs/plugin.py`). skbs itself never calls `.resolve()`/`.absolute()` for you.

## Control-flow exceptions are half-internal

`EndOfPlugin`, `EndOfTemplate`, `ExcludeFile`, `PluginError` (`skbs/pluginutils/__init__.py`) are control-flow signals, not really meant to be caught/raised directly by template authors in general — the sanctioned public surface is `exclude()`, `endOfTemplate()`, `pluginError()`. Exception: `EndOfPlugin`/`PluginError` are *also* handed directly into `plugin.py`'s namespace (so `raise EndOfPlugin()` works there) for backward compatibility with existing templates — kept as-is, documented inline where the namespace is built.

## `Config`/`C()` — why it exists

`skbs.pluginutils.Config` (aliased `C`) is a dict-like, attribute-accessible bag, used for two different things:
1. The framework-injected, fixed-key namespace of plugin.py/per-file templates (now typed via `PluginGlobals`/`FileGlobals`/`SingleFileGlobals` dataclasses, built via `vars(...)` and merged into `Config`).
2. The free-form `plugin`/`_p` object template authors extend with arbitrary attributes (e.g. `plugin.dest = ...`) — deliberately NOT typed/decomposed, since that extensibility is the point.

It predates dataclasses/Pydantic being viable (project started ~Python 3.6); no need to treat it as sacred when refactoring — see the dataclass typing above as an example of layering typing on top of it without replacing it.

## Naming convention

A `_p` suffix means "Path object" (`in_p` = source/template path, `out_p` = output path). Short names (`p`, `d`, `m`, `n`, `g`...) are fine when the scope is short and unambiguous — this codebase intentionally follows a Go-like spirit here rather than blanket-renaming everything.
