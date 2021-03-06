#!/bin/sh
myname=$1
numch=$2
numavg=$3

memsize=`expr $1 \* $2 \* $3 | bc`
upsize=`expr $memsize \* 2 | bc`
# Note: Last '4' is for 32b; other 4's are for tile size
outsize=`echo "$1/4 * ($1/4 + 1) / 2 * 4 * 4 * $2 * 4*2" | bc`

echo $memsize
echo $upsize
echo $outsize

/home/leda/software/psrdada/src/dada_db -d -k dada
/home/leda/software/psrdada/src/dada_db -d -k eada
/home/leda/software/psrdada/src/dada_db -d -k aada
/home/leda/software/psrdada/src/dada_db -d -k bada
/home/leda/software/psrdada/src/dada_db -d -k fada
/home/leda/software/psrdada/src/dada_db -d -k cada
/home/leda/software/psrdada/src/dada_db -d -k adda
/home/leda/software/psrdada/src/dada_db -d -k aeda
/home/leda/software/psrdada/src/dada_db -d -k afda
/home/leda/software/psrdada/src/dada_db -d -k acda
/home/leda/software/psrdada/src/dada_db -d -k abda
/home/leda/software/psrdada/src/dada_db -d -k bcda

/home/leda/software/psrdada/src/dada_db -c 1 -b $memsize -k dada -l
/home/leda/software/psrdada/src/dada_db -c 1 -b $memsize -k adda -l
/home/leda/software/psrdada/src/dada_db -c 9 -b $memsize -k aeda -l
/home/leda/software/psrdada/src/dada_db -c 9 -b $memsize -k eada -l

/home/leda/software/psrdada/src/dada_db -c 9 -b $outsize -k fada -l
/home/leda/software/psrdada/src/dada_db -c 1 -b $outsize -k afda -l
/home/leda/software/psrdada/src/dada_db -c 1 -b $outsize -k cada -l
/home/leda/software/psrdada/src/dada_db -c 9 -b $outsize -k acda -l

/home/leda/software/psrdada/src/dada_db -c 1 -b $upsize -k abda -l
/home/leda/software/psrdada/src/dada_db -c 1 -b $upsize -k aada -l
/home/leda/software/psrdada/src/dada_db -c 9 -b $upsize -k bcda -l
/home/leda/software/psrdada/src/dada_db -c 9 -b $upsize -k bada -l

