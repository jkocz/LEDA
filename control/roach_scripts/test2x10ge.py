#!/usr/bin/env python

import corr,time,numpy,struct,sys

#bitstream = 'testge_2011_Dec_07_1027.bof'
bitstream = 'testge_sys2x.bof'
#bitstream = 'testge_32.bof'
roach     = '169.254.128.14'

dest_ip0   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 30 #192.168.6.7
dest_ip1   = 192*(2**24) + 168*(2**16) + 10*(2**8) +  30 #192.168.6.7
dest_ip2   = 192*(2**24) + 168*(2**16) + 10*(2**8) + 8 #192.168.6.7
dest_ip3   = 192*(2**24) + 168*(2**16) + 7*(2**8) + 8 #192.168.6.7
dest_port0 = 4030
dest_port1 = 4031
dest_port2 = 4081
dest_port3 = 4087

src_ip0    = 192*(2**24) + 168*(2**16) + 10*(2**8) + 22  #192.168.6.10
src_ip1    = 192*(2**24) + 168*(2**16) + 11*(2**8) + 22  #192.168.6.10
src_ip2    = 192*(2**24) + 168*(2**16) + 9*(2**8) + 12  #192.168.6.10
src_ip3    = 192*(2**24) + 168*(2**16) + 7*(2**8) + 13  #192.168.6.10
src_port0  = 4000
src_port1  = 4001
src_port2  = 4002
src_port3  = 4003

mac_base0 = (2<<40) + (2<<32)
mac_base1 = (2<<40) + (2<<32) + 1
mac_base2 = (2<<40) + (2<<32) + 2
mac_base3 = (2<<40) + (2<<32) + 3
gbe0     = 'gbe0'
gbe1     = 'gbe1'
gbe2     = 'gbe2'
gbe3     = 'gbe3'

payload_len = 1026
period      = 2600

print('Connecting to server %s on port... '%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

if fpga.is_connected():
	print 'ok\n'	
else:
	print 'ERROR\n'

print '------------------------'
print 'Programming FPGA with %s...' %bitstream,
fpga.progdev(bitstream)
print 'ok\n'

time.sleep(1)

print '------------------------'
print 'Staring tgtap server...',   
fpga.tap_start('gbe0',gbe0,mac_base0+src_ip0,src_ip0,src_port0)
fpga.tap_start('gbe1',gbe1,mac_base1+src_ip1,src_ip1,src_port1)
fpga.tap_start('gbe2',gbe2,mac_base2+src_ip2,src_ip2,src_port2)
fpga.tap_start('gbe3',gbe3,mac_base3+src_ip3,src_ip3,src_port3)
print 'done'

time.sleep(2)

print '------------------------'
print 'Setting-up packet core...',
sys.stdout.flush()
fpga.write_int('dest_ip2',dest_ip2)
fpga.write_int('dest_port2',dest_port2)
fpga.write_int('pkt_sim2_payload_len', payload_len)
fpga.write_int('pkt_sim2_period', period)

fpga.write_int('dest_ip1',dest_ip1)
fpga.write_int('dest_port1',dest_port1)
fpga.write_int('pkt_sim1_payload_len', payload_len)
fpga.write_int('pkt_sim1_period', period)

fpga.write_int('dest_ip',dest_ip0)
fpga.write_int('dest_port',dest_port0)
fpga.write_int('pkt_sim_payload_len', payload_len)
fpga.write_int('pkt_sim_period', period)

fpga.write_int('dest_ip3',dest_ip3)
fpga.write_int('dest_port3',dest_port3)
fpga.write_int('pkt_sim3_payload_len', payload_len)
fpga.write_int('pkt_sim3_period', period)
time.sleep(1)

fpga.write_int('pkt_sim2_roach_num',0)
fpga.write_int('pkt_sim1_roach_num',0)
fpga.write_int('pkt_sim_roach_num',0)
fpga.write_int('pkt_sim3_roach_num',1)

print '------------------------'
print 'Resetting counter...',
fpga.write_int('enable', 0)
fpga.write_int('rst', 1)
fpga.write_int('rst', 0)
#fpga.write_int('enable', 1)
print 'done'

#print '--------------------------'
#print 'Stopping counter...',
#fpga.write_int('pkt_sim2_enable',0)
#print 'done'

