
import pytest
from pathlib import Path

MINIMAL_PLUGIN = "plugin = C()\n"


@pytest.fixture()
def freshBackend(tmp_path):
  from skbs.backend import Backend
  from skbs.pluginutils import Config as C
  config = C(
    verbose=False,
    template_dir=tmp_path
  )
  return Backend(config), tmp_path


def makeTemplate(tmp_path, name='tpl', plugin=MINIMAL_PLUGIN, root_template=None, nested_template=None):
  """
  Build a minimal multi-file template directory under tmp_path/name, with
  plugin.py, a root/ dir, and optionally a `_template.` file directly in
  root/ (root_template) and/or in a root/sub/ subdirectory (nested_template).
  """
  tpl = tmp_path / name
  (tpl / 'root').mkdir(parents=True)
  (tpl / 'plugin.py').write_text(plugin)
  if root_template is not None :
    (tpl / 'root' / '_template.').write_text(root_template)
  if nested_template is not None :
    (tpl / 'root' / 'sub').mkdir()
    (tpl / 'root' / 'sub' / '_template.').write_text(nested_template)
  return tpl


def test_rootTouch_plainPython_producesEmptyFile(freshBackend, tmp_path):
  B, _ = freshBackend
  tpl = makeTemplate(tmp_path, root_template="touch()\n")
  dest = tmp_path / 'out.txt'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert dest.is_file()
  # OutStream.getvalue() always ends with a newline, even with zero lines
  assert dest.read_text() == '\n'

def test_rootTouch_templated_producesFileWithContent(freshBackend, tmp_path):
  B, _ = freshBackend
  root_template = ' ## # {{__skbs_template__}}\nhello world\n ## touch()\n'
  tpl = makeTemplate(tmp_path, root_template=root_template)
  dest = tmp_path / 'out.txt'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert dest.is_file()
  assert dest.read_text() == 'hello world\n'

def test_root_withoutTouch_staysADirectory(freshBackend, tmp_path):
  B, _ = freshBackend
  tpl = makeTemplate(tmp_path, root_template="new_path = dest\n")
  dest = tmp_path / 'out_dir'
  (tpl / 'root' / 'file.txt').write_text('hi')
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert dest.is_dir()
  assert (dest / 'file.txt').read_text() == 'hi'

def test_nestedDirTouch_becomesFile(freshBackend, tmp_path):
  B, _ = freshBackend
  tpl = makeTemplate(tmp_path, nested_template="touch()\n")
  dest = tmp_path / 'out_dir'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert dest.is_dir()
  assert (dest / 'sub').is_file()
  assert (dest / 'sub').read_text() == '\n'

def test_rootTouch_destExistsAsDirectory_errors(freshBackend, tmp_path):
  B, _ = freshBackend
  tpl = makeTemplate(tmp_path, root_template="touch()\n")
  dest = tmp_path / 'already_a_dir'
  dest.mkdir()
  res, help = B.execTemplate(tpl, str(dest), [])
  assert not res
  assert 'already exists' in help

def test_normalGeneration_destExistsAsFile_errors(freshBackend, tmp_path):
  B, _ = freshBackend
  tpl = makeTemplate(tmp_path)
  (tpl / 'root' / 'file.txt').write_text('hi')
  dest = tmp_path / 'already_a_file'
  dest.write_text('im a file')
  res, help = B.execTemplate(tpl, str(dest), [])
  assert not res
  assert 'already exists' in help
