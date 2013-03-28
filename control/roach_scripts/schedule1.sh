#!/bin/sh
#script to startup entire pipeline - not necessarily recommended, but easy to use
#from a single terminal

# setup data buffers

#~/software/psrdada/src/dada_db -d -k dada
#~/software/psrdada/src/dada_db -d -k eada
#~/software/psrdada/src/dada_db -d -k aada
#~/software/psrdada/src/dada_db -d -k bada
#~/software/psrdada/src/dada_db -d -k fada
#~/software/psrdada/src/dada_db -d -k cada

#sleep 1

#~/software/psrdada/src/dada_db -b 213385216 -k dada -l
#~/software/psrdada/src/dada_db -b 213385216 -k eada -l
#~/software/psrdada/src/dada_db -b 213385216 -k fada -l
#~/software/psrdada/src/dada_db -b 213385216 -k cada -l
#~/software/psrdada/src/dada_db -b 426770432 -k aada -l
#~/software/psrdada/src/dada_db -b 426770432 -k bada -l

#sleep 1

# program roachs

killall dada_dbdisk
killall leda_dbupdb_paper
killall leda_udpdb_thread
killall leda_dbgpu

sleep 2

#/home/leda/roach_scripts/prog_10gall.py
#/home/leda/roach_scripts/write_coeffsr13.py
#/home/leda/roach_scripts/write_coeffsr14.py

#sleep 180
sleep 5

#exec 3>&1 4>&2 >> /home/leda/logs/dbdisk.cada 2>&1
#/home/leda/software/psrdada/src/dada_dbnull -z -k cada &
#exec >> /home/leda/logs/dbdisk.fada 2>&1
#/home/leda/software/psrdada/src/dada_dbnull -z -k fada &
#exec 3>&1 4>&2 >> /home/leda/logs/dbdisk.acda 2>&1
#/home/leda/software/psrdada/src/dada_dbnull -z -k acda & 
#exec >> /home/leda/logs/dbdisk.afda 2>&1
#/home/leda/software/psrdada/src/dada_dbnull -z -k afda & 
exec 3>&1 4>&2 >> /home/leda/logs/dbdisk.cada 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b7 -s -W -k cada -D /data1/one/ & 
exec >> /home/leda/logs/dbdisk.fada 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b14 -s -W -k fada -D /data2/one/ &
exec 3>&1 4>&2 >> /home/leda/logs/dbdisk.acda 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b14 -s -W -k acda -D /data1/two/ & 
exec >> /home/leda/logs/dbdisk.afda 2>&1
/home/leda/software/psrdada/src/dada_dbdisk -b7 -s -W -k afda -D /data2/two/ &
sleep 1
exec >> /home/leda/logs/unpack.bada 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c10 eada bada &
exec >> /home/leda/logs/unpack.aada 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c3 dada aada &
exec >> /home/leda/logs/unpack.abda 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c4 adda abda &
exec >> /home/leda/logs/unpack.bcda 2>&1
/home/leda/software/psrdada/leda/src/leda_dbupdb_paper -c11 aeda bcda &
sleep 1
exec >> /home/leda/logs/dbgpu.fada 2>&1
/home/leda/software/leda_ipp/leda_dbgpu -c12 -g 2 bada fada &
exec >> /home/leda/logs/dbgpu.cada 2>&1
/home/leda/software/leda_ipp/leda_dbgpu -c5 -g 0 aada cada &
exec >> /home/leda/logs/dbgpu.afda 2>&1
/home/leda/software/leda_ipp/leda_dbgpu -c6 -g 1 abda afda &
exec >> /home/leda/logs/dbgpu.acda 2>&1
/home/leda/software/leda_ipp/leda_dbgpu -c13 -g 3 bcda acda &
sleep 1
exec 1>&3 2>&4
