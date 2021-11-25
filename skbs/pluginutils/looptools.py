from itertools import *

def check_first(it):
  return zip(chain((True,), repeat(False)), it)

def check_last(it):
  it = iter(it)
  try :
    v = next(it)
  except StopIteration:
    return
  for nv in it :
    yield False, v
    v = nv
  yield True, v

def check_first_last(it):
  it = iter(it)
  first = True
  try :
    v = next(it)
  except StopIteration:
    return
  for nv in it :
    yield first, False, v
    v = nv
    first = False
  yield first, True, v

