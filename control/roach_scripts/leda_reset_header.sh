#!/bin/sh

#cp /home/leda/software/roach_scripts/header_utc_orig.txt /home/leda/software/roach_scripts/header_utc.txt
#cp /home/leda/software/roach_scripts/headere_utc_orig.txt /home/leda/software/roach_scripts/headere_utc.txt
cp /home/leda/roach_scripts/header64a.txt /home/leda/roach_scripts/header64a_utc.txt
cp /home/leda/roach_scripts/header64b.txt /home/leda/roach_scripts/header64b_utc.txt
cp /home/leda/roach_scripts/header64c.txt /home/leda/roach_scripts/header64c_utc.txt
cp /home/leda/roach_scripts/header64d.txt /home/leda/roach_scripts/header64d_utc.txt

exec >> /home/leda/roach_scripts/header64a_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 
exec >> /home/leda/roach_scripts/header64b_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 
exec >> /home/leda/roach_scripts/header64c_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 
exec >> /home/leda/roach_scripts/header64d_utc.txt
echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S` 
#exec >> /home/leda/software/leda_devel/leda_ipp/headere_utc.txt
#echo "UTC_START" `date -u +%Y-%m-%d-%H:%M:%S`

exec >> /home/leda/logs/udpdb.dada 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 1 -k dada -i 192.168.0.17 -p 4001 -f /home/leda/roach_scripts/header64a_utc.txt -n8 &
exec >> /home/leda/logs/udpdb.adda 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 2 -k adda -i 192.168.0.65 -p 4004 -f /home/leda/roach_scripts/header64b_utc.txt -n8 &
exec >> /home/leda/logs/udpdb.eada 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 15 -k eada -i 192.168.0.49 -p 4003 -f /home/leda/roach_scripts/header64c_utc.txt -n8 &
exec >> /home/leda/logs/udpdb.aeda 2>&1
/home/leda/software/psrdada/leda/src/leda_udpdb_thread -b 9 -k aeda -i 192.168.0.33 -p 4002 -f /home/leda/roach_scripts/header64d_utc.txt -n8 &
exec 1>&3 2>&4

#fpga1.write_int('adc_sub_rst', 0)
#fpga2.write_int('adc_sub_rst', 0)
#fpga3.write_int('adc_sub_rst', 0)
#fpga4.write_int('adc_sub_rst', 0)

#time.sleep(x)

#fpga1.write_int('data_transport1_enable',0)
#fpga2.write_int('data_transport1_enable',0)
#fpga3.write_int('data_transport1_enable',0)
#fpga4.write_int('data_transport1_enable',0)
#print 'disable done\n'

