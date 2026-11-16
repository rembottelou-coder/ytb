#!/bin/bash
# render_soft.sh <name> <seed> <obstacle> <ball> <soft1> <soft2> <soft3>
name=$1; seed=$2; obst=$3; ball=$4; shift 4
mkdir -p shorts/$name
i=0
for sv in "$@"; do
  i=$((i+1)); d=shorts/$name/clip$i; mkdir -p $d
  [ -f $d/done ] && continue
  BALL=$ball python3 soft.py $d $sv ${RES:-0.4} ${SAMPLES:-10} 96 $seed $obst > $d/log.txt 2>&1 && touch $d/done
done
echo FINISHED $name
