
def pathmod(p) :
  p = p.with_name(removePrefix(p.name))
  if 'to_rem' in p.name :
    return True, None
  return True, p
    
