
from pathlib import Path
import traceback
from contextlib import contextmanager
from functools import wraps
from hl037utils.config import Config as C
import pkg_resources
import os

#from dbug import *

from traceback import print_exc

import time
import json

APP = 'hrprotoparser'


class Backend(object):
  def __init__(self, config):
    self.config = config


  @staticmethod
  def createConfig(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), 'wb') as f :
      f.write(pkg_resources.resource_string(APP, 'default/conf.py'))

  def installDefaultTemplates(self):
    from distutils.dir_util import copy_tree
    self.config.template_dir.mkdir(parents=True, exist_ok=True)
    pkg_resources.set_extraction_path(self.config.template_dir)
    dest = str(self.config.template_dir/'default/templates/') + '/'
    src = pkg_resources.resource_filename(APP, 'default/templates/')
    if src != dest :
      copy_tree(src, dest)
    return dest

  def installTemplate(self, name, src):
    from distutils.dir_util import copy_tree
    dest = self.config.template_dir / 'templates' / name
    copy_tree(str(src), str(dest))
    return dest
  
  def uninstallTemplate(self, name):
    from distutils.dir_util import remove_tree
    dest = self.config.template_dir / 'templates' / name
    remove_tree(str(dest))
    return dest

    

