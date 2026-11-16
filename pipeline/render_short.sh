#!/bin/bash
# render_short.sh <name> <palette> <seed> <nslab> <angle1> <angle2> ...   (last angle = success 0)
name=$1; pal=$2; seed=$3; ns=$4; shift 4
mkdir -p shorts/$name
i=0; n=$#
for a in "$@"; do
  i=$((i+1)); d=shorts/$name/clip$i; mkdir -p $d
  if [ $i -eq $n ]; then succ=1; nf=84; else succ=0; nf=78; fi
  [ -f $d/done ] && continue
  python3 scene.py $d $a $succ ${RES:-0.4} ${SAMPLES:-8} $nf $seed $pal $ns 1 $nf > $d/log.txt 2>&1 && touch $d/done
done
echo FINISHED $name
