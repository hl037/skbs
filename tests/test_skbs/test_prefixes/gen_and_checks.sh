# /bin/bash
for o in O o; do
for f in F f; do
for r in R r; do
for t in T t; do
   p=$o$f$r$t;
   rm -r $p;
   echo skbs gen meta $p;
   skbs gen meta $p;
done;
done;
done;
done;
grep -e 'should' -r o*/r/* O*/r/* | grep -v -e not | grep -e '{{42'
grep -e 'should' -r o*/r/* O*/r/* | grep -e not | grep -e ' 42'
grep -e 'not good' -r o*/r/* O*/r/*
