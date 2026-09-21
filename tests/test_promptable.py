
import filecmp
import pytest
from pytest_datadir_ng import datadir
from pathlib import Path
from unittest.mock import patch


def assertDirsEqual(d1, d2):
  cmp = filecmp.dircmp(d1, d2)
  assert cmp.right_only == []
  assert cmp.left_only == []
  assert cmp.diff_files == []


@pytest.fixture(scope='session')
def simpleBackend(tmpdir_factory):
  tmp_path = tmpdir_factory.mktemp('dir')
  from skbs.backend import Backend
  from skbs.pluginutils import Config as C
  config = C(
    verbose=False,
    template_dir=tmp_path
  )
  return Backend(config), tmp_path


def test_promptable_cliArgGiven(simpleBackend, tmp_path, datadir):
  """
  A plugin.py using @promptable, called with the Prompt-marked argument
  already given on the command line: no interactive prompting involved,
  generation goes through the engine exactly like any other template.
  """
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(datadir['r'])
  res, help = B.execTemplate(t, str(tmp_path), ['myservice'])
  assert res, help
  assertDirsEqual(r, tmp_path)


def test_answerFile_replaysAcrossRuns(simpleBackend, tmp_path, tmp_path_factory, monkeypatch, datadir):
  """
  A plugin.py stacking @answer_file on top of @promptable: first run gives
  everything on the CLI (a plain --replicas option and a Prompt-marked
  service name), writing .skbs_answer to the cwd. Second run gives nothing
  on the CLI - replicas is silently replayed from the file, and the
  service prompt shows the stored value as a suggestion, accepted here by
  answering with an empty line. The final generated tree (round 2's
  output) must match the same content as round 1, since the same values
  were reused end to end through the real engine.
  """
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(datadir['r'])

  # .skbs_answer is written relative to the process cwd, not `dest` - keep
  # it out of the tree assertDirsEqual below compares against `r`.
  monkeypatch.chdir(tmp_path_factory.mktemp('cwd'))

  res, help = B.execTemplate(t, str(tmp_path), ['--replicas', '5', '--service', 'myservice'])
  assert res, help

  with patch('builtins.input', lambda *a: ''):
    res, help = B.execTemplate(t, str(tmp_path), [])
  assert res, help

  assertDirsEqual(r, tmp_path)


def test_answerFile_ignoresUnknownKeys(simpleBackend, tmp_path, tmp_path_factory, monkeypatch, datadir):
  """
  A .skbs_answer file can carry a key that doesn't match any parameter of
  the decorated function (e.g. left over from a plugin.py that used to
  have more options) - it must be silently ignored, not raise, and not be
  carried over into the rewritten file after the run.
  """
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(datadir['r'])

  cwd = tmp_path_factory.mktemp('cwd')
  monkeypatch.chdir(cwd)
  answer_path = cwd / '.skbs_answer'
  answer_path.write_text('{"replicas": "5", "service": "myservice", "totally_unknown_key": "whatever"}')

  with patch('builtins.input', lambda *a: ''):
    res, help = B.execTemplate(t, str(tmp_path), [])
  assert res, help

  assertDirsEqual(r, tmp_path)
  assert 'totally_unknown_key' not in answer_path.read_text()
