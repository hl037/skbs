
def pathmod(p):
  assert _p.a == 42
  assert plugin.a == 42
  if 'to_rep' in p.name :
    return True, p.with_name('_template.name_replaced')
  return False, p

