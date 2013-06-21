#!/bin/sh

cp /home/leda/software/roach_scripts/header64a_600.txt /home/leda/software/roach_scripts/header64a_utc.txt
cp /home/leda/software/roach_scripts/header64b_600.txt /home/leda/software/roach_scripts/header64b_utc.txt

exec >> /home/leda/software/roach_scripts/header64a_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 
exec >> /home/leda/software/roach_scripts/header64b_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 

exec >> /home/leda/logs/udpdb.dada 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 1 -k dada -i 192.168.40.5 -p 4015 -f /home/leda/software/roach_scripts/header64a_utc.txt -n8 &
exec >> /home/leda/logs/udpdb.eada 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 2 -k eada -i 192.168.40.5 -p 4016 -f /home/leda/software/roach_scripts/header64b_utc.txt -n8 &
exec 1>&3 2>&4


