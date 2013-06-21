#!/bin/sh
#script to startup entire pipeline - not necessarily recommended, but easy to use
#from a single terminal

killall dada_dbnull
killall dada_dbdisk
killall leda_dbupdb_paper
killall leda_udpdb_thread
killall leda_dbgpu
killall leda_dbxgpu


sleep 2

exec 3>&1 4>&2 >> /home/leda/logs/dbdisk.cada 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b7 -s -W -k cada -D /data1/one/ & 
exec >> /home/leda/logs/dbdisk.fada 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b14 -s -W -k fada -D /data1/two/ &
sleep 1
exec >> /home/leda/logs/unpack.bada 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c10 eada bada &
exec >> /home/leda/logs/unpack.aada 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c3 dada aada &
sleep 1
exec >> /home/leda/logs/dbgpu.fada 2>&1
/home/leda/software/LEDA/xengine/leda_dbxgpu -c12 -d1 -t25 bada fada &
exec >> /home/leda/logs/dbgpu.cada 2>&1
/home/leda/software/LEDA/xengine/leda_dbxgpu -c5 -d0 -t25 aada cada &
#/home/leda/software/leda_ipp/leda_dbgpu -c6 -g 1 abda afda &
sleep 1
exec 1>&3 2>&4
