
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKBS_CMD = [sys.executable, '-m', 'skbs.cli']

BASH_SCRIPT = Path(__file__).parent.parent / 'skbs' / 'default' / 'completion' / 'bash' / '_skbs'
ZSH_SCRIPT = Path(__file__).parent.parent / 'skbs' / 'default' / 'completion' / 'zsh' / '_skbs'

# pytest's tmp_path lives under /tmp, which is mounted noexec in this repo's
# sandbox - the shim script below needs to be executable, so it's placed
# under the repo instead (cleaned up by the fixture).
SHIM_DIR = Path(__file__).parent / '.completion_test_shim'


def _run(env, *args, cwd=None):
  return subprocess.run(SKBS_CMD + list(args), env=env, cwd=cwd, capture_output=True, text=True)


@pytest.fixture()
def shim():
  """
  Shell shim so completion scripts (which invoke `$COMP_WORDS[0]`/`skbs`)
  work regardless of whether the console-script entry point is on PATH in
  the environment running the tests.
  """
  SHIM_DIR.mkdir(exist_ok=True)
  path = SHIM_DIR / 'skbs'
  path.write_text(f'#!/bin/sh\nexec {sys.executable} -m skbs.cli "$@"\n')
  path.chmod(0o755)
  yield path
  shutil.rmtree(SHIM_DIR, ignore_errors=True)


@pytest.fixture()
def skbsEnv(tmp_path):
  cfg = tmp_path / 'cfg'
  data = tmp_path / 'data'
  env = {**os.environ, 'XDG_CONFIG_HOME': str(cfg), 'XDG_DATA_HOME': str(data)}
  r = _run(env, 'create-config')
  assert r.returncode == 0, r.stderr
  return env


def test_completeTemplates_listsInstalledTemplates(skbsEnv):
  r = _run(skbsEnv, 'install-defaults')
  assert r.returncode == 0, r.stderr
  r = _run(skbsEnv, '_complete-templates', '@sk')
  assert '@skbs' in r.stdout.splitlines()
  assert '@skbs.sft' in r.stdout.splitlines()

def test_completeTemplates_reflectsInstallState(skbsEnv, tmp_path):
  """
  The whole point of the custom protocol is that completion is computed
  live from the current install state, not baked in at generation time.
  """
  r = _run(skbsEnv, '_complete-templates', '@my')
  assert r.stdout == ''
  src = tmp_path / 'mytemplate.txt'
  src.write_text('hello')
  _run(skbsEnv, 'install', str(src))
  r = _run(skbsEnv, '_complete-templates', '@my')
  assert '@mytemplate.txt' in r.stdout.splitlines()
  _run(skbsEnv, 'uninstall', 'mytemplate.txt')
  r = _run(skbsEnv, '_complete-templates', '@my')
  assert r.stdout == ''

def test_completeTemplates_localDirectory(skbsEnv, tmp_path):
  # A directory that is itself a valid template (has a `root/`) is listed
  # as-is, without a trailing slash - the slash is only added for plain
  # browseable subdirectories (see Backend.findTemplates/_findTemplates).
  (tmp_path / 'mytemplate' / 'root').mkdir(parents=True)
  r = _run(skbsEnv, '_complete-templates', 'mytemp', cwd=tmp_path)
  assert 'mytemplate' in r.stdout.splitlines()


@pytest.fixture()
def namespacedTemplate(skbsEnv, tmp_path):
  """
  An installed template that is itself a namespace directory containing a
  real template one level down (like the shipped cpp/class example) -
  `@mynamespace` is browseable, `@mynamespace/class` is the actual template.
  """
  (tmp_path / 'ns' / 'class' / 'root').mkdir(parents=True)
  (tmp_path / 'ns' / 'class' / 'plugin.py').touch()
  r = _run(skbsEnv, 'install', str(tmp_path / 'ns'), '-n', 'mynamespace')
  assert r.returncode == 0, r.stderr
  return skbsEnv

def test_completeTemplates_nested_topLevelPartialPrefix(namespacedTemplate):
  r = _run(namespacedTemplate, '_complete-templates', '@my')
  assert r.stdout.splitlines() == ['@mynamespace/']

def test_completeTemplates_nested_topLevelExactNoSlash(namespacedTemplate):
  r = _run(namespacedTemplate, '_complete-templates', '@mynamespace')
  assert r.stdout.splitlines() == ['@mynamespace/']

def test_completeTemplates_nested_trailingSlash_noDuplicatedPrefix(namespacedTemplate):
  r = _run(namespacedTemplate, '_complete-templates', '@mynamespace/')
  assert r.stdout.splitlines() == ['@mynamespace/class']

def test_completeTemplates_nested_leafPrefix(namespacedTemplate):
  r = _run(namespacedTemplate, '_complete-templates', '@mynamespace/cl')
  assert r.stdout.splitlines() == ['@mynamespace/class']
  r = _run(namespacedTemplate, '_complete-templates', '@mynamespace/zz')
  assert r.stdout == ''

def test_bashCompletion_dynamicTemplateNames(skbsEnv, shim):
  r = _run(skbsEnv, 'install-defaults')
  assert r.returncode == 0, r.stderr
  script = f'''
  source "{BASH_SCRIPT}"
  COMP_WORDS=("{shim}" gen "@sk")
  COMP_CWORD=2
  _skbs "{shim}"
  echo "${{COMPREPLY[@]}}"
  '''
  r = subprocess.run(['bash', '-c', script], env=skbsEnv, capture_output=True, text=True)
  assert r.returncode == 0, r.stderr
  words = r.stdout.split()
  assert '@skbs' in words
  assert '@skbs.sft' in words

def test_bashCompletion_aliasG_sameAsGen(skbsEnv, shim):
  _run(skbsEnv, 'install-defaults')
  script = f'''
  source "{BASH_SCRIPT}"
  COMP_WORDS=("{shim}" g "@sk")
  COMP_CWORD=2
  _skbs "{shim}"
  echo "${{COMPREPLY[@]}}"
  '''
  r = subprocess.run(['bash', '-c', script], env=skbsEnv, capture_output=True, text=True)
  assert '@skbs' in r.stdout.split()

def test_bashCompletion_commandNames(skbsEnv, shim):
  """
  The bug this whole file exists to catch: `skbs <TAB>` must list the
  subcommands (this is the static part cyclopts generates natively from
  the actual @app.command(...) declarations - no custom protocol needed).
  """
  script = f'''
  source "{BASH_SCRIPT}"
  COMP_WORDS=("{shim}" "ge")
  COMP_CWORD=1
  _skbs "{shim}"
  echo "${{COMPREPLY[@]}}"
  '''
  r = subprocess.run(['bash', '-c', script], env=skbsEnv, capture_output=True, text=True)
  assert r.returncode == 0, r.stderr
  assert r.stdout.split() == ['gen']

def test_bashCompletion_flagNames(skbsEnv, shim):
  script = f'''
  source "{BASH_SCRIPT}"
  COMP_WORDS=("{shim}" install "--sy")
  COMP_CWORD=2
  _skbs "{shim}"
  echo "${{COMPREPLY[@]}}"
  '''
  r = subprocess.run(['bash', '-c', script], env=skbsEnv, capture_output=True, text=True)
  assert '--symlink' in r.stdout.split()

def test_zshCompletionScript_syntaxIsValid():
  r = subprocess.run(['zsh', '-n', str(ZSH_SCRIPT)], capture_output=True, text=True)
  assert r.returncode == 0, r.stderr

def test_zshCompletionScript_hasDynamicTemplateHook():
  # Full interactive zsh completion (compinit + real Tab press via a pty)
  # is too flaky/timing-sensitive to assert on reliably here (zsh's
  # compadd only works from within a real completion widget dispatch) -
  # this at least locks in that the generated+patched script still wires
  # the dynamic hook to the "gen"/"g" TEMPLATE positional, which is the
  # one thing cyclopts' own generator can't produce on its own.
  src = ZSH_SCRIPT.read_text()
  assert '_skbs_complete_template_names' in src
  assert src.count(":_skbs_complete_template_names'") == 2  # gen + its alias g
