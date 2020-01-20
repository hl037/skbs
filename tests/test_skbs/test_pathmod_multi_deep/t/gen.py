
try:
  from pathlib import Path
  from hl037utils.config import Config as C

  root = Path('.')/'root'

  names = ('to_rem', 'to_keep', 'to_transform')
  prefixes = ('', '_template.', '_opt.', '_opt._template.')
  content = [
    lambda n: f'file {n}\nnot good\n''not evaluated : {{42}}\n',
    lambda n: f'file {n}\nnot good\n''evaluated : {{42}}\n',
    lambda n: f'file {n}\ngood\n''not evaluated : {{42}}\n',
    lambda n: f'file {n}\ngood\n''evaluated : {{42}}\n',
  ]

  def create(cur_path, cur_depth, ctx):
    for n, j, p in ( (ctx.i + j, j, cur_path/f'{prefix}_file_{n}_{ctx.i+j}') for j, prefix in enumerate(prefixes) for n in names )  :
      with p.open('w') as f :
        f.write(content[j](n))
    ctx.i += len(prefixes)
    if cur_depth == 0 :
      return
    for p in ( cur_path/f'subdir_{n}_{ctx.i}' for n in names ) :
      p.mkdir(exist_ok=True)
      create(p, cur_depth - 1, ctx)

  create(root, 2, C(i=0))
except:
  import pdb; pdb.xpm()

