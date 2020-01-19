import pytest
from pytest_datadir_ng import datadir, datadir_copy


@pytest.fixture(scope='session')
def simpleBackend(tmpdir_factory):
  tmp_path = tmpdir_factory.mktemp('dir')
  from skbs.backend import Backend
  from hl037utils.config import Config as C
  config = C(
    verbose=False,
    template_dir=tmp_path
  )
  return Backend(config), tmp_path

