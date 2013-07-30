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

dest_port0 = 4015
dest_port1 = 4016

src_ip_base    = 192*(2**24) + 168*(2**16) + 40*(2**8) + 50  

src_port0  = 4000
src_port1  = 4001

mac_base0 = (2<<40) + (2<<32)

gbe0     = 'gbe0'
gbe1     = 'gbe1'

roach=roach7
i=6

print('Connecting to server %s on port... '%(roach)),
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)

time.sleep(1)

if fpga.is_connected():
	print 'ok\n'	
else:
	print 'ERROR\n'
	
print '------------------------'
print 'Staring tgtap server...\n',   
fpga.tap_start(gbe0,'tenge_gbe00',mac_base0+src_ip_base+(i*2),src_ip_base+(i*2),src_port0)
fpga.tap_start(gbe1,'tenge_gbe01',mac_base0+src_ip_base+(i*2)+1,src_ip_base+(i*2)+1,src_port1)

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

fpga.write_int('fft_fft_shift',65535);

odata = numpy.ones(4096,'l')*(1500<<7)
cstr = struct.pack('>4096l',*odata)

fpga.write('fft_f_coeffs1',cstr)
fpga.write('fft_f_coeffs2',cstr)
fpga.write('fft_f_coeffs3',cstr)
fpga.write('fft_f_coeffs4',cstr)
fpga.write('fft_f_coeffs5',cstr)
fpga.write('fft_f_coeffs6',cstr)
fpga.write('fft_f_coeffs7',cstr)
fpga.write('fft_f_coeffs8',cstr)
fpga.write('fft_f1_coeffs1',cstr)
fpga.write('fft_f1_coeffs2',cstr)
fpga.write('fft_f1_coeffs3',cstr)
fpga.write('fft_f1_coeffs4',cstr)
fpga.write('fft_f1_coeffs5',cstr)
fpga.write('fft_f1_coeffs6',cstr)
fpga.write('fft_f1_coeffs7',cstr)
fpga.write('fft_f1_coeffs8',cstr)
fpga.write('fft_f2_coeffs1',cstr)
fpga.write('fft_f2_coeffs2',cstr)
fpga.write('fft_f2_coeffs3',cstr)
fpga.write('fft_f2_coeffs4',cstr)
fpga.write('fft_f2_coeffs5',cstr)
fpga.write('fft_f2_coeffs6',cstr)
fpga.write('fft_f2_coeffs7',cstr)
fpga.write('fft_f2_coeffs8',cstr)
fpga.write('fft_f3_coeffs1',cstr)
fpga.write('fft_f3_coeffs2',cstr)
fpga.write('fft_f3_coeffs3',cstr)
fpga.write('fft_f3_coeffs4',cstr)
fpga.write('fft_f3_coeffs5',cstr)
fpga.write('fft_f3_coeffs6',cstr)
fpga.write('fft_f3_coeffs7',cstr)
fpga.write('fft_f3_coeffs8',cstr)



print '------------------------\n'
print 'Resetting counter...\n',
fpga.write_int('tenge_enable', 0)
fpga.write_int('adc_rst', 3)
#fpga.write_int('adc_rst', 0)
#fpga.write_int('enable', 1)
print 'done'
