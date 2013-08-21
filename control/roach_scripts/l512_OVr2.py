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

#roach_array = ('rofl1', 'rofl2','rofl3','rofl4','rofl5','rofl6','rofl7'
#	       'rofl8', 'rofl9','rofl10','rofl11','rofl12','rofl13','rofl14'
#	       'rofl15','rofl16')

roach_array = ('rofl1','rofl2', 'rofl3','rofl4','rofl5', 'rofl6',
	       'rofl8', 'rofl9','rofl10','rofl11','rofl13','rofl14',
	       'rofl15', 'rofl16')
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


i = 0

for roach2 in (roach_array):

	#roach2 = roach_array(i);
	print('Connecting to server %s on port... '%(roach2)),
	fpga = corr.katcp_wrapper.FpgaClient(roach2, 7147)

	time.sleep(1)

	if fpga.is_connected():
		print 'ok\n'	
	else:
		print 'ERROR\n'
	
	#fpga.progdev('l512_dev_20130717.bof')

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

	fpga.write_int('tenge_start_count',1252);
	fpga.write_int('tenge_stop_count',1470);
	fpga.write_int('tenge_high_ch',109);

	fpga.write_int('fft_fft_shift',65535);

	odata = numpy.ones(4096,'l')*(1500<<7)
	cstr = struct.pack('>4096l',*odata)

	#fpga.write('fft_f1_coeffs',cstr)
	#fpga.write('fft_f1_coeffs1',cstr)
	#fpga.write('fft_f2_coeffs',cstr)
	#fpga.write('fft_f2_coeffs1',cstr)
	#fpga.write('fft_f3_coeffs',cstr)
	#fpga.write('fft_f3_coeffs1',cstr)
	#fpga.write('fft_f4_coeffs',cstr)
	#fpga.write('fft_f4_coeffs1',cstr)



	print '------------------------\n'
	print 'Resetting counter...\n',
	fpga.write_int('tenge_enable', 0)
	#fpga.write_int('fft_rst', 3)
	fpga.write_int('adc_rst', 3)
	#fpga.write_int('enable', 1)
	print 'done'
        i=i+1


	if i==6:
	   i=i+1
#print '--------------------------'
#print 'Stopping counter...',
#fpga.write_int('pkt_sim2_enable',0)
#print 'done'

#fpga.write_int('tenge_enable',0)
#fpga.write_int('fft_rst',3)
#fpga.write_int('tenge_enable',1)
#fpga.write_int('fft_rst',0)
#fpga.write_int('fft_force_sync',1)
#fpga.write_int('fft_force_sync',0)

