
def pathmod(p) :
  p = p.with_name(removePrefix(p.name))
  if 'to_rem' in p.name :
    return True, None
  if 'to_transform' in p.name :
    return True, p.with_name(p.name.replace('to_transform', 'new_name'))
  return True, p
    
