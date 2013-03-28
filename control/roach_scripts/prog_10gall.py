#!/usr/bin/env python

import corr,time,numpy,struct,sys

roach     = '169.254.128.14'
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)
time.sleep(2)

#boffile = 'l64x8_06022013.bof'
#fpga.progdev(boffile)

time.sleep(1)

starting_ch = 1250
stop_ch = 3650
high_ch = 300

dest_ip0   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 17 #192.168.6.7
dest_ip1   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 33 #192.168.6.7
dest_ip2   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 49 #192.168.6.7
dest_ip3   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 65 #192.168.6.7
dest_ip4   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 81 #192.168.6.7
dest_ip5   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 97 #192.168.6.7
dest_ip6   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 113 #192.168.6.7
dest_ip7   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 129 #192.168.6.7
#dest_ip0   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip1   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip2   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip3   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip4   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip5   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip6   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip7   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 4 #192.168.6.7
#dest_ip0   = 192*(2**24) + 168*(2**16) + 10*(2**8) + 4 #192.168.6.7
#dest_ip1   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 5 #192.168.6.7
#dest_ip2   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 6 #192.168.6.7
#dest_ip3   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 7 #192.168.6.7
#dest_ip4   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 8 #192.168.6.7
#dest_ip5   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 9 #192.168.6.7
#dest_ip6   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 10 #192.168.6.7
#dest_ip7   = 192*(2**24) + 168*(2**16) + 11*(2**8) + 11 #192.168.6.7
dest_port0 = 4001
dest_port1 = 4002
dest_port2 = 4003
dest_port3 = 4004
dest_port4 = 4005
dest_port5 = 4006
dest_port7 = 4007
dest_port6 = 4008

src_ip0    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 145  #192.168.6.11
src_ip1    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 146  #192.168.6.11
src_ip2    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 147  #192.168.6.11
src_ip3    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 148  #192.168.6.11
src_ip4    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 149  #192.168.6.11
src_ip5    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 150  #192.168.6.11
src_ip6    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 151  #192.168.6.11
src_ip7    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 152  #192.168.6.11
#src_ip0    = 192*(2**24) + 168*(2**16) +40*(2**8)  + 11  #192.168.6.11
#src_ip1    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 12  #192.168.6.11
#src_ip2    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 13  #192.168.6.11
#src_ip3    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 14  #192.168.6.11
#src_ip4    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 15  #192.168.6.11
#src_ip5    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 16  #192.168.6.11
#src_ip6    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 17  #192.168.6.11
#src_ip7    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 18  #192.168.6.11
#src_ip0    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 11  #192.168.6.11
#src_ip1    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 12  #192.168.6.11
#src_ip2    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 13  #192.168.6.11
#src_ip3    = 192*(2**24) + 168*(2**16) + 6*(2**8) + 14  #192.168.6.11
#src_ip4    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 15  #192.168.6.11
#src_ip5    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 16  #192.168.6.11
#src_ip6    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 17  #192.168.6.11
#src_ip7    = 192*(2**24) + 168*(2**16) + 6*(2**8) + 18  #192.168.6.11
src_port0  = 4010
src_port1  = 4011
src_port2  = 4012
src_port3  = 4013
src_port4  = 4014
src_port5  = 4015
src_port6  = 4016
src_port7  = 4017

mac_base = (2<<40) + (2<<32)

gbe0     = 'gbe0'
gbe1     = 'gbe1'
gbe2     = 'gbe2'
gbe3     = 'gbe3'
gbe4     = 'gbe4'
gbe5     = 'gbe5'
gbe6     = 'gbe6'
gbe7     = 'gbe7'


fpga.write_int('adc_rst',3)
fpga.write_int('tenge_start_count',starting_ch)
fpga.write_int('tenge_high_ch',high_ch)
fpga.write_int('tenge_stop_count',stop_ch)
fpga.write_int('fft_fft_shift',65535)

fpga.tap_start('gbe0','tenge_gbe00',mac_base+src_ip0,src_ip0,src_port0)
fpga.tap_start('gbe1','tenge_gbe01',mac_base+src_ip1,src_ip1,src_port1)
fpga.tap_start('gbe2','tenge_gbe02',mac_base+src_ip2,src_ip2,src_port2)
fpga.tap_start('gbe3','tenge_gbe03',mac_base+src_ip3,src_ip3,src_port3)
fpga.tap_start('gbe4','tenge_gbe10',mac_base+src_ip4,src_ip4,src_port4)
fpga.tap_start('gbe5','tenge_gbe11',mac_base+src_ip5,src_ip5,src_port5)
fpga.tap_start('gbe6','tenge_gbe12',mac_base+src_ip6,src_ip6,src_port6)
fpga.tap_start('gbe7','tenge_gbe13',mac_base+src_ip7,src_ip7,src_port7)
#fpga.tap_start('gbe7','data_transport1_gbe1',mac_base+src_ip1,src_ip1,src_port1)

time.sleep(1)

sys.stdout.flush()
fpga.write_int('tenge_ips_ip1',dest_ip0)
fpga.write_int('tenge_ips_ip2',dest_ip1)
fpga.write_int('tenge_ips_ip3',dest_ip2)
fpga.write_int('tenge_ips_ip4',dest_ip3)
fpga.write_int('tenge_ips_ip5',dest_ip4)
fpga.write_int('tenge_ips_ip6',dest_ip5)
fpga.write_int('tenge_ips_ip7',dest_ip6)
fpga.write_int('tenge_ips_ip8',dest_ip7)
fpga.write_int('tenge_ports_port1',dest_port0)
fpga.write_int('tenge_ports_port2',dest_port1)
fpga.write_int('tenge_ports_port3',dest_port2)
fpga.write_int('tenge_ports_port4',dest_port3)
fpga.write_int('tenge_ports_port5',dest_port4)
fpga.write_int('tenge_ports_port6',dest_port5)
fpga.write_int('tenge_ports_port7',dest_port6)
fpga.write_int('tenge_ports_port8',dest_port7)
#fpga.print_10gbe_core_details('data_transport1_gbe2')
#fpga.print_10gbe_core_details('data_transport1_gbe1')
#fpga.write_int('data_transport1_payload_len2',814)

fpga.write_int('tenge_f1_fid',0)
fpga.write_int('tenge_f2_fid',1)
fpga.write_int('tenge_f3_fid',2)
fpga.write_int('tenge_f4_fid',3)

print 'programming ROACH complete'
time.sleep(1)

print('Starting data flow...\n')
fpga.write_int('tenge_enable',1)
time.sleep(1)

#fpga.write_int('adc_rst', 0)
#fpga.write_int('adc_force_sync',1)
#time.sleep(1)
#fpga.write_int('adc_force_sync',0)
#fpga.write_int('tenge_enable',0)
#fpga.write_int('adc_rst', 3)


roach     = '169.254.128.13'
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)
time.sleep(2)

#boffile = 'l64x8_06022013.bof'
#fpga.progdev(boffile)

src_ip0    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 161  #192.168.6.11
src_ip1    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 162  #192.168.6.11
src_ip2    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 163  #192.168.6.11
src_ip3    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 164  #192.168.6.11
src_ip4    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 165  #192.168.6.11
src_ip5    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 166  #192.168.6.11
src_ip6    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 167  #192.168.6.11
src_ip7    = 192*(2**24) + 168*(2**16) + 0*(2**8)  + 168  #192.168.6.11
#src_ip0    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 11  #192.168.6.11
#src_ip1    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 12  #192.168.6.11
#src_ip2    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 13  #192.168.6.11
#src_ip3    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 14  #192.168.6.11
#src_ip4    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 15  #192.168.6.11
#src_ip5    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 16  #192.168.6.11
#src_ip6    = 192*(2**24) + 168*(2**16) + 40*(2**8)  + 17  #192.168.6.11
#src_ip7    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 18  #192.168.6.11
#src_ip0    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 11  #192.168.6.11
#src_ip1    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 12  #192.168.6.11
#src_ip2    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 13  #192.168.6.11
#src_ip3    = 192*(2**24) + 168*(2**16) + 6*(2**8) + 14  #192.168.6.11
#src_ip4    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 15  #192.168.6.11
#src_ip5    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 16  #192.168.6.11
#src_ip6    = 192*(2**24) + 168*(2**16) + 6*(2**8)  + 17  #192.168.6.11
#src_ip7    = 192*(2**24) + 168*(2**16) + 6*(2**8) + 18  #192.168.6.11
src_port0  = 4020
src_port1  = 4021
src_port2  = 4022
src_port3  = 4023
src_port4  = 4024
src_port5  = 4025
src_port6  = 4026
src_port7  = 4027

mac_base = (2<<40) + (2<<32)

gbe0     = 'gbe0'
gbe1     = 'gbe1'
gbe2     = 'gbe2'
gbe3     = 'gbe3'
gbe4     = 'gbe4'
gbe5     = 'gbe5'
gbe6     = 'gbe6'
gbe7     = 'gbe7'


fpga.write_int('adc_rst',3)
fpga.write_int('tenge_start_count',starting_ch)
fpga.write_int('tenge_high_ch',high_ch)
fpga.write_int('tenge_stop_count',stop_ch)
fpga.write_int('fft_fft_shift',65535)

fpga.tap_start('gbe0','tenge_gbe00',mac_base+src_ip0,src_ip0,src_port0)
fpga.tap_start('gbe1','tenge_gbe01',mac_base+src_ip1,src_ip1,src_port1)
fpga.tap_start('gbe2','tenge_gbe02',mac_base+src_ip2,src_ip2,src_port2)
fpga.tap_start('gbe3','tenge_gbe03',mac_base+src_ip3,src_ip3,src_port3)
fpga.tap_start('gbe4','tenge_gbe10',mac_base+src_ip4,src_ip4,src_port4)
fpga.tap_start('gbe5','tenge_gbe11',mac_base+src_ip5,src_ip5,src_port5)
fpga.tap_start('gbe6','tenge_gbe12',mac_base+src_ip6,src_ip6,src_port6)
fpga.tap_start('gbe7','tenge_gbe13',mac_base+src_ip7,src_ip7,src_port7)
#fpga.tap_start('gbe7','data_transport1_gbe1',mac_base+src_ip1,src_ip1,src_port1)

time.sleep(1)

sys.stdout.flush()
fpga.write_int('tenge_ips_ip1',dest_ip0)
fpga.write_int('tenge_ips_ip2',dest_ip1)
fpga.write_int('tenge_ips_ip3',dest_ip2)
fpga.write_int('tenge_ips_ip4',dest_ip3)
fpga.write_int('tenge_ips_ip5',dest_ip4)
fpga.write_int('tenge_ips_ip6',dest_ip5)
fpga.write_int('tenge_ips_ip7',dest_ip6)
fpga.write_int('tenge_ips_ip8',dest_ip7)
fpga.write_int('tenge_ports_port1',dest_port0)
fpga.write_int('tenge_ports_port2',dest_port1)
fpga.write_int('tenge_ports_port3',dest_port2)
fpga.write_int('tenge_ports_port4',dest_port3)
fpga.write_int('tenge_ports_port5',dest_port4)
fpga.write_int('tenge_ports_port6',dest_port5)
fpga.write_int('tenge_ports_port7',dest_port6)
fpga.write_int('tenge_ports_port8',dest_port7)
#fpga.print_10gbe_core_details('data_transport1_gbe2')
#fpga.print_10gbe_core_details('data_transport1_gbe1')
#fpga.write_int('data_transport1_payload_len2',814)

fpga.write_int('tenge_f1_fid',4)
fpga.write_int('tenge_f2_fid',5)
fpga.write_int('tenge_f3_fid',6)
fpga.write_int('tenge_f4_fid',7)

print 'programming ROACH complete'
time.sleep(1)

print('Starting data flow...\n')
fpga.write_int('tenge_enable',1)
time.sleep(1)

#fpga.write_int('adc_rst', 0)
#fpga.write_int('adc_force_sync',1)
#time.sleep(1)
#fpga.write_int('adc_force_sync',0)
#fpga.write_int('tenge_enable',0)
#fpga.write_int('adc_rst', 3)

