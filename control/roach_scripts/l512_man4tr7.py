#!/usr/bin/env python

import corr,time,numpy,struct,sys

roach1     = 'rofl1'
roach2     = 'rofl2'
roach3     = 'rofl3'
roach4     = 'rofl4'
roach5     = 'rofl5'
roach6     = 'rofl6'
roach7     = 'rofl7'
roach8     = 'rofl8'
roach9     = 'rofl9'
roach10    = 'rofl10'
roach11    = 'rofl11'
roach12    = 'rofl12'
roach13    = 'rofl13'
roach14    = 'rofl14'
roach15    = 'rofl15'
roach16    = 'rofl16'

dest_ip0   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 10 
dest_ip1   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 11
dest_ip2   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 12
dest_ip3   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 13 
dest_ip4   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 14 
dest_ip5   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 15 
dest_ip6   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 16 
dest_ip7   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 17 
dest_ip8   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 18 
dest_ip9   = 192*(2**24) + 168*(2**16) + 40*(2**8) + 19 
dest_ip10  = 192*(2**24) + 168*(2**16) + 40*(2**8) + 20 

dest_mac0 = 2*(2**32) + 201*(2**24) +  70*(2**16) +  32*(2**8) + 144 # 00:02:c9:46:20:90
dest_mac1 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 155*(2**8) +  16 # 00:02:c9:ec:9b:10
dest_mac2 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 154*(2**8) + 128 # 00:02:c9:ec:9a:80
dest_mac3 = 2*(2**32) + 201*(2**24) +  70*(2**16) +  32*(2**8) +  00 # 00:02:c9:46:20:00
dest_mac4 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 156*(2**8) +  00 # 00:02:c9:ec:9c:00
dest_mac5 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 156*(2**8) +  64 # 00:02:c9:ec:9c:40
dest_mac6 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 151*(2**8) + 160 # 00:02:c9:ec:97:A0
dest_mac7 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 156*(2**8) + 160 # 00:02:c9:ec:9c:A0
dest_mac8 = 2*(2**32) + 201*(2**24) +  70*(2**16) +  25*(2**8) +  80 # 00:02:c9:46:19:50
dest_mac9 = 2*(2**32) + 201*(2**24) + 236*(2**16) + 154*(2**8) + 208 # 00:02:c9:ec:9a:d0
dest_mac10= 2*(2**32) + 201*(2**24) + 236*(2**16) + 155*(2**8) + 240 # 00:02:c9:ec:9b:f0

rofl1_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 50 # 02:02:c0:a8:28:32 
rofl1_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 51 # 02:02:c0:a8:28:33 
rofl2_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 52 # 02:02:c0:a8:28:34 
rofl2_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 53 # 02:02:c0:a8:28:35 
rofl3_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 54 # 02:02:c0:a8:28:36 
rofl3_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 55 # 02:02:c0:a8:28:37 
rofl4_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 56 # 02:02:c0:a8:28:38 
rofl4_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 57 # 02:02:c0:a8:28:39 
rofl5_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 58 # 02:02:c0:a8:28:3a 
rofl5_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 59 # 02:02:c0:a8:28:3b 
rofl6_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 60 # 02:02:c0:a8:28:3c 
rofl6_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 61 # 02:02:c0:a8:28:3d 
rofl7_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 62 # 02:02:c0:a8:28:3e 
rofl7_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 63 # 02:02:c0:a8:28:3f 
rofl8_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 64 # 02:02:c0:a8:28:40 
rofl8_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 65 # 02:02:c0:a8:28:41
rofl9_mac0  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 66 # 02:02:c0:a8:28:42 
rofl9_mac1  = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 67 # 02:02:c0:a8:28:43
rofl10_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 68 # 02:02:c0:a8:28:44 
rofl10_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 69 # 02:02:c0:a8:28:45
rofl11_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 70 # 02:02:c0:a8:28:46 
rofl11_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 71 # 02:02:c0:a8:28:47
rofl12_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 72 # 02:02:c0:a8:28:48 
rofl12_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 73 # 02:02:c0:a8:28:49
rofl13_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 74 # 02:02:c0:a8:28:4a 
rofl13_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 75 # 02:02:c0:a8:28:4b
rofl14_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 76 # 02:02:c0:a8:28:4c 
rofl14_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 77 # 02:02:c0:a8:28:4d
rofl15_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 78 # 02:02:c0:a8:28:4e 
rofl15_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 79 # 02:02:c0:a8:28:4f
rofl16_mac0 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 80 # 02:02:c0:a8:28:50 
rofl16_mac1 = 2*(2**40) + 2*(2**32) + 192*(2**24) + 168*(2**16) + 40*(2**8) + 81 # 02:02:c0:a8:28:51


dest_macff= 255*(2**40) + 255*(2**32) + 255*(2**24) + 255*(2**16) + 255*(2**8) + 255

arp_table = [dest_macff for i in range(256)]

arp_table[10] = dest_mac0
arp_table[11] = dest_mac1
arp_table[12] = dest_mac2
arp_table[13] = dest_mac3
arp_table[14] = dest_mac4
arp_table[15] = dest_mac5
arp_table[16] = dest_mac6
arp_table[17] = dest_mac7
arp_table[18] = dest_mac8
arp_table[19] = dest_mac9
arp_table[20] = dest_mac10


arp_table[50] = rofl1_mac0
arp_table[51] = rofl1_mac1
arp_table[52] = rofl2_mac0
arp_table[53] = rofl2_mac1
arp_table[54] = rofl3_mac0
arp_table[55] = rofl3_mac1
arp_table[56] = rofl4_mac0
arp_table[57] = rofl4_mac1
arp_table[58] = rofl5_mac0
arp_table[59] = rofl5_mac1
arp_table[60] = rofl6_mac0
arp_table[61] = rofl6_mac1
arp_table[62] = rofl7_mac0
arp_table[63] = rofl7_mac1
arp_table[64] = rofl8_mac0
arp_table[65] = rofl8_mac1
arp_table[66] = rofl9_mac0
arp_table[67] = rofl9_mac1
arp_table[68] = rofl10_mac0
arp_table[69] = rofl10_mac1
arp_table[70] = rofl11_mac0
arp_table[71] = rofl11_mac1
arp_table[72] = rofl12_mac0
arp_table[73] = rofl12_mac1
arp_table[74] = rofl13_mac0
arp_table[75] = rofl13_mac1
arp_table[76] = rofl14_mac0
arp_table[77] = rofl14_mac1
arp_table[78] = rofl15_mac0
arp_table[79] = rofl15_mac1
arp_table[80] = rofl16_mac0
arp_table[81] = rofl16_mac1

dest_port0 = 4015
dest_port1 = 4016

src_ip_base    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 50  

src_port0  = 4000
src_port1  = 4001

mac_base0 = (2<<40) + (2<<32)

gbe0     = 'gbe0'
gbe1     = 'gbe1'


i = 6
roach = roach7


print('Connecting to server %s on port... '%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

if fpga.is_connected():
	print 'ok\n'	
else:
	print 'ERROR\n'
	

print '------------------------'
print 'Enable 10gbe core...\n',   

fpga.config_10gbe_core('tenge_gbe00', mac_base0+src_ip_base+(i*2), src_ip_base+(i*2), src_port0, arp_table)
fpga.config_10gbe_core('tenge_gbe01', mac_base0+src_ip_base+(i*2)+1, src_ip_base+(i*2)+1, src_port1, arp_table)

time.sleep(2)

print '------------------------\n'
print 'Setting-up packet core...\n',
sys.stdout.flush()

fpga.write_int('tenge_port1',dest_port0)
fpga.write_int('tenge_port2',dest_port1)

fpga.write_int('tenge_ips_ip1',dest_ip0)
fpga.write_int('tenge_ips_ip2',dest_ip1)
fpga.write_int('tenge_ips_ip3',dest_ip2)
fpga.write_int('tenge_ips_ip4',dest_ip3)
fpga.write_int('tenge_ips_ip5',dest_ip4)
fpga.write_int('tenge_ips_ip6',dest_ip5)
fpga.write_int('tenge_ips_ip7',dest_ip6)
fpga.write_int('tenge_ips_ip8',dest_ip7)
fpga.write_int('tenge_ips_ip9',dest_ip8)
fpga.write_int('tenge_ips_ip10',dest_ip9)
fpga.write_int('tenge_ips_ip11',dest_ip10)
fpga.write_int('tenge_ips_ip12',dest_ip0)
fpga.write_int('tenge_ips_ip13',dest_ip1)
fpga.write_int('tenge_ips_ip14',dest_ip2)
fpga.write_int('tenge_ips_ip15',dest_ip3)
fpga.write_int('tenge_ips_ip16',dest_ip4)
fpga.write_int('tenge_ips_ip17',dest_ip5)
fpga.write_int('tenge_ips_ip18',dest_ip6)
fpga.write_int('tenge_ips_ip19',dest_ip7)
fpga.write_int('tenge_ips_ip20',dest_ip8)
fpga.write_int('tenge_ips_ip21',dest_ip9)
fpga.write_int('tenge_ips_ip22',dest_ip10)

fpga.write_int('tenge_header_fid',i)

fpga.write_int('tenge_start_count',1246);
fpga.write_int('tenge_stop_count',1464);
fpga.write_int('tenge_high_ch',109);

fpga.write_int('fft_f1_fft_shift',65535);
fpga.write_int('fft_f2_fft_shift',65535);
fpga.write_int('fft_f3_fft_shift',65535);
fpga.write_int('fft_f4_fft_shift',65535);

odata = numpy.ones(4096,'l')*(1500<<7)
cstr = struct.pack('>4096l',*odata)

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



print 'Resetting counter...\n',
fpga.write_int('tenge_enable', 0)
fpga.write_int('adc_rst', 3)
print 'done'

