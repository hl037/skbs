
import io

import pytest

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


@pytest.fixture()
def patchedGetBackend(monkeypatch, freshBackend):
  """
  `skbs.gen()` called outside a running template fetches its own Backend via
  `configutils.getBackend()` (reading the real on-disk config) - point it at
  the disposable per-test Backend instead.
  """
  B, tmp_path = freshBackend
  import skbs.configutils as configutils
  monkeypatch.setattr(configutils, 'getBackend', lambda *a, **k: B)
  return B, tmp_path


def installUserTemplate(tmp_path, name, content):
  p = tmp_path / 'templates' / name
  p.parent.mkdir(parents=True, exist_ok=True)
  p.write_text(content)
  return p


def test_gen_outsideTemplate_atRequiresOutF(patchedGetBackend):
  import skbs
  with pytest.raises(ValueError):
    skbs.gen('@inner', '@')


def test_gen_outsideTemplate_writesToOutF(patchedGetBackend):
  B, tmp_path = patchedGetBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  import skbs
  out = io.StringIO()
  res = skbs.gen('@inner', '@', out_f=out)
  assert res[0], res[1]
  assert out.getvalue() == 'hello from inner\n'


def test_gen_outsideTemplate_destRelativeToCwd(patchedGetBackend, tmp_path, monkeypatch):
  B, _ = patchedGetBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  workdir = tmp_path / 'workdir'
  workdir.mkdir()
  monkeypatch.chdir(workdir)
  import skbs
  res, help = skbs.gen('@inner', 'out.txt')
  assert res, help
  assert (workdir / 'out.txt').read_text() == 'hello from inner\n'


def test_gen_outsideTemplate_traversalNotRestricted(patchedGetBackend, tmp_path):
  B, _ = patchedGetBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  import skbs
  dest = tmp_path / 'escaped.txt'
  res, help = skbs.gen('@inner', str(dest))
  assert res, help
  assert dest.read_text() == 'hello from inner\n'


def test_gen_outsideTemplate_variadicArgsAndResult(patchedGetBackend, tmp_path):
  B, _ = patchedGetBackend
  installUserTemplate(tmp_path, 'vartpl', " ## _p.args_received = list(args)\n")
  import skbs
  from skbs.pluginutils import Config as C
  r = C()
  res, help = skbs.gen('@vartpl', str(tmp_path / 'dest.txt'), 'a1', 'a2', result=r)
  assert res, help
  assert r._p.args_received == ['a1', 'a2']


def test_gen_outsideTemplate_resultIgnoredForMultiFileTemplate(patchedGetBackend, tmp_path):
  B, _ = patchedGetBackend
  tpl = tmp_path / 'multi'
  (tpl / 'root').mkdir(parents=True)
  (tpl / 'plugin.py').write_text(MINIMAL_PLUGIN)
  (tpl / 'root' / 'file.txt').write_text('static content\n')
  import skbs
  from skbs.pluginutils import Config as C
  r = C()
  res, help = skbs.gen(str(tpl), str(tmp_path / 'out_dir'), result=r)
  assert res, help
  assert len(r) == 0


def test_gen_insidePlugin_relativeToTemplateRoot(freshBackend):
  B, tmp_path = freshBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  tpl = tmp_path / 'outer'
  (tpl / 'root').mkdir(parents=True)
  (tpl / 'plugin.py').write_text(MINIMAL_PLUGIN)
  (tpl / 'root' / '_template.file.txt').write_text(" ## skbs.gen('@inner', '@')\n")
  dest = tmp_path / 'out'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert (dest / 'file.txt').read_text() == 'hello from inner\n'


def test_gen_insideDirTemplate_relativeToGovernedDir(freshBackend):
  B, tmp_path = freshBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  tpl = tmp_path / 'tpl2'
  (tpl / 'root' / 'sub').mkdir(parents=True)
  (tpl / 'plugin.py').write_text(MINIMAL_PLUGIN)
  (tpl / 'root' / 'sub' / '_template.').write_text("skbs.gen('@inner', 'nested_out')\n")
  dest = tmp_path / 'out2'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert dest.is_dir()
  assert (dest / 'sub').is_dir()
  assert (dest / 'sub' / 'nested_out').read_text() == 'hello from inner\n'


def test_gen_insidePlugin_traversalGuardRaisesPluginError(freshBackend):
  B, tmp_path = freshBackend
  installUserTemplate(tmp_path, 'inner', 'hello from inner\n')
  tpl = tmp_path / 'tpl3'
  (tpl / 'root').mkdir(parents=True)
  (tpl / 'plugin.py').write_text(
    "plugin = C()\n"
    "try:\n"
    "  skbs.gen('@inner', '../../escape')\n"
    "  help = 'no error raised'\n"
    "except PluginError as e:\n"
    "  help = e.help\n"
  )
  dest = tmp_path / 'out3'
  res, help = B.execTemplate(tpl, str(dest), [])
  assert res, help
  assert 'escapes' in help
