#!/usr/bin/env python

import corr,time,numpy,struct,sys

roach     = '169.254.128.14'

dest_ip0   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 17 #192.168.6.7
#dest_ip1   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 49 #192.168.6.7
dest_ip1   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 33 #192.168.6.7
dest_ip2   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 81 #192.168.6.7
dest_ip3   = 192*(2**24) + 168*(2**16) + 0*(2**8) + 113 #192.168.6.7
dest_port0 = 4001
dest_port1 = 4003
dest_port2 = 4005
dest_port3 = 4008

src_ip0    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 145  #192.168.6.10
src_ip1    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 146  #192.168.6.10
src_port0  = 4010
src_port1  = 4011

src_ip2    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 149  #192.168.6.10
src_ip3    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 150  #192.168.6.10

mac_base0 = (2<<40) + (2<<32)
mac_base1 = (2<<40) + (2<<32) + 1
gbe0     = 'gbe0'
gbe1     = 'gbe1'

dest_mac0 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 96 #
#dest_mac1 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 254*(2**8) + 140 #
dest_mac1 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 254*(2**8) + 141 #
dest_mac2 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 120 #
#dest_mac1 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 121 #
dest_mac3 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 84 #
#dest_mac3 = 15*(2**32) + 83*(2**24) + 12*(2**16) + 255*(2**8) + 85 #

print('Connecting to server %s on port... \n'%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

#print 'Staring tgtap server...\n',   
#fpga.tap_start(gbe0,'tenge_gbe00',mac_base0+src_ip0,src_ip0,src_port0)
#fpga.tap_start(gbe1,'tenge_gbe01',mac_base1+src_ip1,src_ip1,src_port1)
print 'Configuring transmitter cores...\n',
sys.stdout.flush()

#Configure 10GbE cores and install tgtap drivers.
print ('Configuring the 10GbE cores...\n'),
# setup arp_table = ff:ff:ff:ff:ff:ff for all
dest_macff= 255*(2**32) + 255*(2**24) + 255*(2**16) + 255*(2**8) + 255 #00:0f:53:0c:ff:78
arp_table = [dest_macff for i in range(256)]

arp_table[17] = dest_mac0
#arp_table[49] = dest_mac1
arp_table[33] = dest_mac1
arp_table[81] = dest_mac2
arp_table[113] = dest_mac3

#arp_table[146] = dest_mac4
#arp_table[147] = dest_mac5
#arp_table[114]= dest_mac6
#arp_table[130]= dest_mac7

fpga_mac1 = mac_base0 + src_ip0
fpga_mac2 = mac_base1 + src_ip1
fpga_mac3 = mac_base0 + src_ip2
fpga_mac4 = mac_base1 + src_ip3

arp_table[145] = fpga_mac1
arp_table[146] = fpga_mac2
arp_table[149] = fpga_mac3
arp_table[150] = fpga_mac4
#arp_table[82] = fpga_mac5
#arp_table[98] = fpga_mac6
#arp_table[114]= fpga_mac7
#arp_table[130]= fpga_mac8

#print(arp_table)
fpga.config_10gbe_core('tenge_gbe00', mac_base0+src_ip0, src_ip0, src_port0, arp_table)
fpga.config_10gbe_core('tenge_gbe01', mac_base1+src_ip1, src_ip1, src_port1, arp_table)

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

#fpga.write_int('fft_fft_shift',65535);
fpga.write_int('fft_f1_fft_shift',65535);
fpga.write_int('fft_f2_fft_shift',65535);
fpga.write_int('fft_f3_fft_shift',65535);
fpga.write_int('fft_f4_fft_shift',65535);


odata = numpy.ones(4096,'l')*(700<<7)
cstr = struct.pack('>4096l',*odata)

odata0 = numpy.zeros(4096,'l')
cstr0 = struct.pack('>4096l',*odata0)
#fpga.write('fft_f1_coeffs',cstr)
#fpga.write('fft_f1_coeffs1',cstr)
#fpga.write('fft_f2_coeffs',cstr)
#fpga.write('fft_f2_coeffs1',cstr)
#fpga.write('fft_f3_coeffs',cstr)
#fpga.write('fft_f3_coeffs1',cstr)
#fpga.write('fft_f4_coeffs',cstr)
#fpga.write('fft_f4_coeffs1',cstr)

fpga.write('fft_f1_coeff_eq0_coeffs',cstr)
fpga.write('fft_f1_coeff_eq1_coeffs',cstr)
fpga.write('fft_f1_coeff_eq2_coeffs',cstr)
fpga.write('fft_f1_coeff_eq3_coeffs',cstr)
fpga.write('fft_f1_coeff_eq4_coeffs',cstr)
fpga.write('fft_f1_coeff_eq5_coeffs',cstr)
fpga.write('fft_f1_coeff_eq6_coeffs',cstr)
fpga.write('fft_f1_coeff_eq7_coeffs',cstr)
fpga.write('fft_f2_coeff_eq0_coeffs',cstr)
fpga.write('fft_f2_coeff_eq1_coeffs',cstr)
fpga.write('fft_f2_coeff_eq2_coeffs',cstr)
fpga.write('fft_f2_coeff_eq3_coeffs',cstr)
fpga.write('fft_f2_coeff_eq4_coeffs',cstr)
fpga.write('fft_f2_coeff_eq5_coeffs',cstr)
fpga.write('fft_f2_coeff_eq6_coeffs',cstr)
fpga.write('fft_f2_coeff_eq7_coeffs',cstr)
fpga.write('fft_f3_coeff_eq0_coeffs',cstr)
fpga.write('fft_f3_coeff_eq1_coeffs',cstr)
fpga.write('fft_f3_coeff_eq2_coeffs',cstr)
fpga.write('fft_f3_coeff_eq3_coeffs',cstr)
fpga.write('fft_f3_coeff_eq4_coeffs',cstr)
fpga.write('fft_f3_coeff_eq5_coeffs',cstr)
fpga.write('fft_f3_coeff_eq6_coeffs',cstr)
fpga.write('fft_f3_coeff_eq7_coeffs',cstr)
fpga.write('fft_f4_coeff_eq0_coeffs',cstr)
fpga.write('fft_f4_coeff_eq1_coeffs',cstr)
fpga.write('fft_f4_coeff_eq2_coeffs',cstr)
fpga.write('fft_f4_coeff_eq3_coeffs',cstr)
fpga.write('fft_f4_coeff_eq4_coeffs',cstr)
fpga.write('fft_f4_coeff_eq5_coeffs',cstr)
fpga.write('fft_f4_coeff_eq6_coeffs',cstr)
fpga.write('fft_f4_coeff_eq7_coeffs',cstr)



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


roach     = '169.254.128.13'

src_ip0    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 149  #192.168.6.10
src_ip1    = 192*(2**24) + 168*(2**16) + 0*(2**8) + 150  #192.168.6.10
src_port0  = 4014
src_port1  = 4015

mac_base0 = (2<<40) + (2<<32)
mac_base1 = (2<<40) + (2<<32) + 1
gbe0     = 'gbe0'
gbe1     = 'gbe1'


print('Connecting to server %s on port... \n'%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

print 'Configuring transmitter cores...\n',
sys.stdout.flush()

#Configure 10GbE cores and install tgtap drivers.
print ('Configuring the 10GbE cores...\n'),

fpga.config_10gbe_core('tenge_gbe00', mac_base0+src_ip0, src_ip0, src_port0, arp_table)
fpga.config_10gbe_core('tenge_gbe01', mac_base1+src_ip1, src_ip1, src_port1, arp_table)
#print '------------------------'
#print 'Staring tgtap server...\n',   
#fpga.tap_start('tenge_gbe00',gbe0,mac_base0+src_ip0,src_ip0,src_port0)
#fpga.tap_start('tenge_gbe01',gbe1,mac_base1+src_ip1,src_ip1,src_port1)
#fpga.tap_start(gbe0,'tenge_gbe00',mac_base0+src_ip0,src_ip0,src_port0)
#fpga.tap_start(gbe1,'tenge_gbe01',mac_base1+src_ip1,src_ip1,src_port1)

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

fpga.write_int('tenge_header_fid',4)
fpga.write_int('tenge_header_fid2',5)
fpga.write_int('tenge_header_fid3',6)
fpga.write_int('tenge_header_fid4',7)

fpga.write_int('tenge_start_count',1250);
fpga.write_int('tenge_stop_count',2450);
fpga.write_int('tenge_high_ch',600);

#fpga.write_int('fft_fft_shift',65535);

fpga.write_int('fft_f1_fft_shift',65535);
fpga.write_int('fft_f2_fft_shift',65535);
fpga.write_int('fft_f3_fft_shift',65535);
fpga.write_int('fft_f4_fft_shift',65535);

odata = numpy.ones(4096,'l')*(700<<7)
cstr = struct.pack('>4096l',*odata)

odata0 = numpy.zeros(4096,'l')
cstr0 = struct.pack('>4096l',*odata0)
#fpga.write('fft_f1_coeffs',cstr)
#fpga.write('fft_f1_coeffs1',cstr)
#fpga.write('fft_f2_coeffs',cstr)
#fpga.write('fft_f2_coeffs1',cstr)
#fpga.write('fft_f3_coeffs',cstr)
#fpga.write('fft_f3_coeffs1',cstr)
#fpga.write('fft_f4_coeffs',cstr)
#fpga.write('fft_f4_coeffs1',cstr)

fpga.write('fft_f1_coeff_eq0_coeffs',cstr)
fpga.write('fft_f1_coeff_eq1_coeffs',cstr)
fpga.write('fft_f1_coeff_eq2_coeffs',cstr)
fpga.write('fft_f1_coeff_eq3_coeffs',cstr)
fpga.write('fft_f1_coeff_eq4_coeffs',cstr)
fpga.write('fft_f1_coeff_eq5_coeffs',cstr)
fpga.write('fft_f1_coeff_eq6_coeffs',cstr)
fpga.write('fft_f1_coeff_eq7_coeffs',cstr)
fpga.write('fft_f2_coeff_eq0_coeffs',cstr)
fpga.write('fft_f2_coeff_eq1_coeffs',cstr)
fpga.write('fft_f2_coeff_eq2_coeffs',cstr)
fpga.write('fft_f2_coeff_eq3_coeffs',cstr)
fpga.write('fft_f2_coeff_eq4_coeffs',cstr)
fpga.write('fft_f2_coeff_eq5_coeffs',cstr)
fpga.write('fft_f2_coeff_eq6_coeffs',cstr)
fpga.write('fft_f2_coeff_eq7_coeffs',cstr)
fpga.write('fft_f3_coeff_eq0_coeffs',cstr)
fpga.write('fft_f3_coeff_eq1_coeffs',cstr)
fpga.write('fft_f3_coeff_eq2_coeffs',cstr)
fpga.write('fft_f3_coeff_eq3_coeffs',cstr)
fpga.write('fft_f3_coeff_eq4_coeffs',cstr)
fpga.write('fft_f3_coeff_eq5_coeffs',cstr)
fpga.write('fft_f3_coeff_eq6_coeffs',cstr)
fpga.write('fft_f3_coeff_eq7_coeffs',cstr)
fpga.write('fft_f4_coeff_eq0_coeffs',cstr)
fpga.write('fft_f4_coeff_eq1_coeffs',cstr)
fpga.write('fft_f4_coeff_eq2_coeffs',cstr)
fpga.write('fft_f4_coeff_eq3_coeffs',cstr)
fpga.write('fft_f4_coeff_eq4_coeffs',cstr)
fpga.write('fft_f4_coeff_eq5_coeffs',cstr)
fpga.write('fft_f4_coeff_eq6_coeffs',cstr)
fpga.write('fft_f4_coeff_eq7_coeffs',cstr)



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

