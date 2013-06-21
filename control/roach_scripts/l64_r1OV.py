#!/usr/bin/env python

import corr,time,numpy,struct,sys

roach     = 'roach2-l1'

dest_ip0   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 5 #192.168.6.7
dest_ip1   = 192*(2**24) + 168*(2**16) + 40*(2**8) +  5 #192.168.6.7
dest_ip2   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 6 #192.168.6.7
dest_ip3   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 6 #192.168.6.7
#dest_ip0   = 192*(2**24) + 168*(2**16) + 1*(2**8) + 40 #192.168.6.7
#dest_ip1   = 192*(2**24) + 168*(2**16) + 1*(2**8) + 40  #192.168.6.7
#dest_ip2   = 192*(2**24) + 168*(2**16) + 1*(2**8) + 40 #192.168.6.7
#dest_ip3   = 192*(2**24) + 168*(2**16) + 1*(2**8) + 40  #192.168.6.7
dest_port0 = 4015
dest_port1 = 4016
dest_port2 = 4017
dest_port3 = 4018

src_ip0    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 50  #192.168.6.10
src_ip1    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 51  #192.168.6.10
src_ip2    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 52  #192.168.6.10
src_ip3    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 53  #192.168.6.10
#src_ip0    = 192*(2**24) + 168*(2**16) + 1*(2**8) + 50  #192.168.6.10
#src_ip1    = 192*(2**24) + 168*(2**16) + 1*(2**8) + 51  #192.168.6.10
#src_ip2    = 192*(2**24) + 168*(2**16) + 1*(2**8) + 52  #192.168.6.10
#src_ip3    = 192*(2**24) + 168*(2**16) + 1*(2**8) + 53  #192.168.6.10
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
period      = 8000

print('Connecting to server %s on port... '%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

if fpga.is_connected():
	print 'ok\n'	
else:
	print 'ERROR\n'

#print '------------------------'
#print 'Programming FPGA with %s...' %bitstream,
#fpga.progdev(bitstream)
#print 'ok\n'

#time.sleep(1)

print '------------------------'
print 'Staring tgtap server...\n',   
#fpga.tap_start('tenge_gbe00',gbe0,mac_base0+src_ip0,src_ip0,src_port0)
#fpga.tap_start('tenge_gbe01',gbe1,mac_base1+src_ip1,src_ip1,src_port1)
fpga.tap_start(gbe0,'tenge_gbe00',mac_base0+src_ip0,src_ip0,src_port0)
fpga.tap_start(gbe1,'tenge_gbe01',mac_base1+src_ip1,src_ip1,src_port1)

time.sleep(2)

print '------------------------\n'
print 'Setting-up packet core...\n',
sys.stdout.flush()
fpga.write_int('tenge_ips_ip1',dest_ip0)
fpga.write_int('tenge_ips_port1',dest_port0)

fpga.write_int('tenge_ips_ip2',dest_ip1)
fpga.write_int('tenge_ips_port2',dest_port1)

fpga.write_int('tenge_ips_ip3',dest_ip2)
fpga.write_int('tenge_ips_port3',dest_port2)

fpga.write_int('tenge_ips_ip4',dest_ip3)
fpga.write_int('tenge_ips_port4',dest_port3)

time.sleep(1)

fpga.write_int('tenge_header_fid',0)
fpga.write_int('tenge_header_fid2',1)
fpga.write_int('tenge_header_fid3',2)
fpga.write_int('tenge_header_fid4',3)

fpga.write_int('tenge_start_count',1250);
fpga.write_int('tenge_stop_count',2450);
fpga.write_int('tenge_high_ch',600);

fpga.write_int('fft_fft_shift',65535);

odata = numpy.ones(4096,'l')*(700<<7)
cstr = struct.pack('>4096l',*odata)

odata0 = numpy.zeros(4096,'l')
cstr0 = struct.pack('>4096l',*odata0)
fpga.write('fft_f1_coeffs',cstr)
fpga.write('fft_f1_coeffs1',cstr)
fpga.write('fft_f2_coeffs',cstr)
fpga.write('fft_f2_coeffs1',cstr)
fpga.write('fft_f3_coeffs',cstr)
fpga.write('fft_f3_coeffs1',cstr)
fpga.write('fft_f4_coeffs',cstr)
fpga.write('fft_f4_coeffs1',cstr)



print '------------------------\n'
print 'Resetting counter...\n',
fpga.write_int('tenge_enable', 0)
fpga.write_int('adc_rst', 3)
fpga.write_int('adc_rst', 0)
#fpga.write_int('enable', 1)
print 'done'

#print '--------------------------'
#print 'Stopping counter...',
#fpga.write_int('pkt_sim2_enable',0)
#print 'done'

