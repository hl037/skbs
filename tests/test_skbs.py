
import filecmp
import pytest
from pytest_datadir_ng import datadir, datadir_copy
from pathlib import Path

from dbug import *

def assertDirsEqual(d1, d2):
  cmp = filecmp.dircmp(d1, d2)
  assert cmp.right_only == []
  assert cmp.left_only == []
  assert cmp.diff_files == []

def assertFilesEqual(f1, f2):
  assert filecmp.cmp(f1, f2, shallow=False)


@pytest.fixture()
def freshBackend(tmp_path):
  from skbs.backend import Backend
  from skbs.pluginutils import Config as C
  config = C(
    verbose=False,
    template_dir=tmp_path
  )
  return Backend(config), tmp_path

def test_createConfig(tmp_path, datadir):
  from skbs.backend import Backend as B
  conf = datadir['default/conf.py']
  B.createConfig(tmp_path / 'conf.py')
  assertFilesEqual(conf, tmp_path / 'conf.py')

def test_installDefaultTemplates(freshBackend, datadir):
  B, tmp_path = freshBackend
  B.installDefaultTemplates(False)
  src_templates = datadir['default/templates']
  target_templates = tmp_path / 'default/templates'
  assertDirsEqual(target_templates, src_templates)
  
def test_installDefaultTemplates_symlink(freshBackend, datadir):
  B, tmp_path = freshBackend
  B.installDefaultTemplates(True)
  src_templates = datadir['default/templates']
  target_templates = tmp_path / 'default/templates'
  assertDirsEqual(target_templates, src_templates)
  
def test_installTemplate(freshBackend, datadir):
  B, tmp_path = freshBackend
  t1 = Path(datadir['t1'])
  B.installTemplate('t1', t1, False)
  target_templates = tmp_path / 'templates/t1'
  assertDirsEqual(target_templates, t1)

def test_uninstallTemplate(freshBackend, datadir):
  B, tmp_path = freshBackend
  t1 = Path(datadir['t1'])
  B.installTemplate('t1', t1, False)
  B.uninstallTemplate('t1')
  target_templates = tmp_path / 'templates/t1'
  assert not target_templates.exists()
  
def test_installTemplate_symlink(freshBackend, datadir):
  B, tmp_path = freshBackend
  t1 = Path(datadir['t1'])
  B.installTemplate('t1', t1, True)
  target_templates = tmp_path / 'templates/t1'
  assertDirsEqual(target_templates, t1)

def test_uninstallTemplate_symlink(freshBackend, datadir):
  B, tmp_path = freshBackend
  t1 = Path(datadir['t1'])
  B.installTemplate('t1', t1, True)
  B.uninstallTemplate('t1')
  target_templates = tmp_path / 'templates/t1'
  assert not target_templates.exists()
  
def test_installTemplate_over(freshBackend, datadir):
  B, tmp_path = freshBackend
  t1 = Path(datadir['t1'])
  t2 = Path(datadir['t2'])
  B.installTemplate('t1', t1)
  B.installTemplate('t1', t2)
  target_templates = tmp_path / 'templates/t1'
  assertDirsEqual(target_templates, t2)

  

# Processing tests :

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


def doTestProcessing(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(datadir['r'])
  B.execTemplate(t, str(tmp_path), [42, 43])
  assertDirsEqual(r, tmp_path)
  
def doTestProcessingSFT(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(datadir['r'])
  B.execTemplate(t, str(tmp_path/'res'), [42, 43])
  assertFilesEqual(r, tmp_path / 'res')
  
def doTestProcessing2(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  tt = Path(datadir['tt'])
  r = Path(datadir['r'])
  B.execTemplate(t, str(tmp_path), [42, 43])
  B.execTemplate(tt, str(tmp_path), [42, 43])
  assertDirsEqual(r, tmp_path)

def test_simple(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_subdirs(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_noplugin(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_withopt(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  tt = Path(datadir['tt'])
  r = Path(datadir['r'])
  B.execTemplate(t, str(tmp_path), [42, 43])
  B.execTemplate(tt, str(tmp_path), [42, 43])
  assertDirsEqual(r, tmp_path)

def test_withtemplate(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_withoptandtemplate(simpleBackend, tmp_path, datadir):
  doTestProcessing2(simpleBackend, tmp_path, datadir)



@pytest.mark.parametrize(
  'dir',
  [
    ''.join(('oO'[o], 'fF'[f], 'rR'[r], 'tT'[t]))
    for o, f, r, t in (
      map(int ,f'{i:0>4b}')
      for i in range(16)
    )
  ]
)
def test_prefixes(simpleBackend, tmp_path, datadir, dir):
  B, _ = simpleBackend
  d = Path(datadir[dir])
  t = d / 't'
  tt = d / 'tt'
  r = d / 'r'
  B.execTemplate(t, str(tmp_path), [42, 43])
  B.execTemplate(tt, str(tmp_path), [42, 43])
  assertDirsEqual(r, tmp_path)

def test_tempiny_mod(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_varplugin(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_args(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_include(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_include_scope(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)


def test_include_args(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)
  

def test_pathmod(simpleBackend, tmp_path, datadir):
  doTestProcessing2(simpleBackend, tmp_path, datadir)
  
  
def test_pathmod(simpleBackend, tmp_path, datadir):
  doTestProcessing2(simpleBackend, tmp_path, datadir)
  
  
def test_infile_pathmod(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)
  

def test_dir_template(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)
  
  
def test_empty_dirs(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  r = Path(tmp_path/'r')
  dirs = [
    'to_keep2',
    'to_keep2/to_keep2_to_keep',
    'to_keep2/to_keep2_to_keep2',
    'to_keep2/moved',
    'to_keep',
    'to_keep/to_keep_to_keep2',
    'to_keep/to_keep_to_keep',
    'to_keep/moved',
    'moved',
    'moved/to_move_to_keep',
    'moved/to_move_to_keep2',
    'moved/moved',
  ]
  for d in dirs :
    Dvar(r"""d, r/d""")
    (r/d).mkdir(parents=True, exist_ok=True)
  B.execTemplate(t, str(tmp_path/'o'), [42, 43])
  assertDirsEqual(r, tmp_path/'o')
  
  
def test_end_of_template(simpleBackend, tmp_path, datadir):
  doTestProcessing(simpleBackend, tmp_path, datadir)
  
  
def test_help(simpleBackend, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  b, h = B.execTemplate(t, '@help', None)
  assert not b
  assert 'Dummy help' == h
  
def test_help_docstring(simpleBackend, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  b, h = B.execTemplate(t, '@help', None)
  assert not b
  assert 'Dummy help' == h
  b, h = B.execTemplate(t, '_help', ['--help'])
  assert not b
  assert 'Dummy help' == h
  
def test_help_forced(simpleBackend, tmp_path, datadir):
  B, _ = simpleBackend
  t = Path(datadir['t'])
  b, h = B.execTemplate(t, str(tmp_path/'_'), None)
  assert not b
  assert 'Dummy help' == h
  assert not (tmp_path/'_').exists()


def test_sections(simpleBackend, tmp_path, datadir, datadir_copy):
  B, _ = simpleBackend
  doTestProcessing(simpleBackend, tmp_path, datadir)
  t = Path(datadir['t'])
  r2_ = Path(datadir_copy['r2_'])
  r2 = Path(datadir['r2'])
  B.execTemplate(t, str(r2_), None)
  assertDirsEqual(r2, r2_)

def test_placeholder(simpleBackend, tmp_path, datadir, datadir_copy):
  B, _ = simpleBackend
  doTestProcessing(simpleBackend, tmp_path, datadir)
  t = Path(datadir['t'])
  r1_ = Path(datadir_copy['r1_'])
  r1 = Path(datadir['r1'])
  B.execTemplate(t, str(r1_), None)
  assertDirsEqual(r1, r1_)
  r2_ = Path(datadir_copy['r2_'])
  r2 = Path(datadir['r2'])
  B.execTemplate(t, str(r2_), None)
  assertDirsEqual(r2, r2_)
  r3_ = Path(datadir_copy['r3_'])
  r3 = Path(datadir['r3'])
  B.execTemplate(t, str(r3_), None)
  assertDirsEqual(r3, r3_)
  r4_ = Path(datadir_copy['r4_'])
  r4 = Path(datadir['r4'])
  B.execTemplate(t, str(r4_), None)
  assertDirsEqual(r4, r4_)
  
def test_sft(simpleBackend, tmp_path, datadir):
  doTestProcessingSFT(simpleBackend, tmp_path, datadir)
  
def test_sft_include(simpleBackend, tmp_path, datadir):
  doTestProcessingSFT(simpleBackend, tmp_path, datadir)
  
def test_sft_plugin(simpleBackend, tmp_path, datadir):
  doTestProcessingSFT(simpleBackend, tmp_path, datadir)
  
  

