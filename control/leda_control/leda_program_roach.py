#!/usr/bin/env python

import corr,time,numpy,struct,sys
import subprocess

def ip2int(address):
	c = [int(x) for x in address.split('.')]
	return (c[0]<<24) | (c[1]<<16) | (c[2]<<8) | c[3]

def programRoach(fpga, boffile, fids, src_ips, src_ports,
                 dest_ips, dest_ports,
                 first_chan, last_chan, nchans, gain_coef,
                 have_adcs=True, use_progdev=False,
                 registers={}, fft_shift_mask=0xFFFF):
	print "Writing program"
	if use_progdev:
		fpga.progdev(boffile)
	else:
		#output = open(os.devnull, 'w')
		if len(registers) > 0:
			regstring = "-r " + ','.join(["0x%x=0x%x" % (key,val) for key,val in registers.items()])
		else:
			regstring = ""
		ret = subprocess.call("adc16_init.rb %s -v %s %s" % (regstring, fpga.host, boffile),
							  shell=True)
							  #stdout=output, stderr=output)
		if ret != 0:
			print "ERROR: Programming failed!", ret
			return -1
		#output.close()
	time.sleep(1)
	
	print "Setting program configuration"
	reset_cmd = 'adc_rst' if have_adcs else 'fft_rst'
	fpga.write_int(reset_cmd, 3)
	fpga.write_int('tenge_start_count', first_chan)
	fpga.write_int('tenge_high_ch',     nchans)
	fpga.write_int('tenge_stop_count',  last_chan)
	if fft_shift_mask is not None:
		fpga.write_int('fft_fft_shift',     fft_shift_mask)
	
	print "Setting network configuration"
	mac_base = (2<<40) + (2<<32)
	
	for i, (src_ip, src_port) in enumerate(zip(src_ips, src_ports)):
		fpga.tap_start('gbe%i'%i, 'tenge_gbe%i%i'%(i/4,i%4),
		               mac_base+ip2int(src_ip), ip2int(src_ip), src_port)
	
	for i, dest_port in enumerate(dest_ports):
		fpga.write_int('tenge_port%i'%(i+1), dest_port)
		for j, dest_ip in enumerate(dest_ips):
			ii = i*len(dest_ips) + j
			fpga.write_int('tenge_ips_ip%i'%(ii+1), ip2int(dest_ip))
	
	try:
		fpga.write_int('tenge_header_fid', fids[0])
	except TypeError:
		fpga.write_int('tenge_header_fid', fids)
	else:
		for i, fid in enumerate(fids[1:]):
			fpga.write_int('tenge_header_fid%i'%(i+2), fid)
		
	print "Writing gain coefficients"
	# TODO: Allow passing in arrays of input- and channel-specific coefs
	if gain_coef is not None:
		odata = numpy.ones(4096,'l') * gain_coef
		cstr = struct.pack('>4096l',*odata)
		odata0 = numpy.zeros(4096,'l')
		cstr0 = struct.pack('>4096l',*odata0)
		for i in range(4):
			fpga.write('fft_f%i_coeffs' %(i+1),cstr)
			fpga.write('fft_f%i_coeffs1'%(i+1),cstr0)
	
	print "Resetting counter"
	fpga.write_int('tenge_enable', 0)
	fpga.write_int(reset_cmd, 3)
	
	print "Done"

if __name__ == "__main__":
	from configtools import *
	import sys
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	execfile(configfile, globals())
	
	# TODO: Consider spawning these in separate threads to save time
	for i in xrange(len(roachhosts)):
		print "Programming ROACH %i @ %s" % (i, roachhosts[i])
		print "---------------------"
		fpga  = corr.katcp_wrapper.FpgaClient(roachhosts[i], roachport)
		time.sleep(1)
		if not fpga.is_connected():
			print "ERROR: Failed to connect to FPGA", roachhosts[i]
			sys.exit(-1)
		
		programRoach(fpga, boffile, fids[i], src_ips[i], src_ports,
		             dest_ips, dest_ports,
		             fft_first_chan, fft_last_chan, nchan, fft_gain_coef,
		             have_adcs=have_adcs, use_progdev=use_progdev,
		             registers=roach_registers,
		             fft_shift_mask=fft_shift_mask)
		
	print "All done"
	print "Please wait 3 minutes for settings to take effect"
