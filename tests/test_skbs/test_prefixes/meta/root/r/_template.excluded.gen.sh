# /bin/bash
## exclude()

for o in 0 1; do 
for f in 0 1; do
for r in 0 1; do
for t in 0 1; do
for h in 0 1; do
for d in 0 1; do
for v in 0 1; do
  if [ "$o$f$r$t$h$d$v" != 0000000 ]; then
    ln -s txt00.00.000 txt$o$f.$r$t.$h$d$v
  fi
done
done
done
done
done
done
done
