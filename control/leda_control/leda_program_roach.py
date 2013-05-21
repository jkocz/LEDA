#!/usr/bin/env python

import corr,time,numpy,struct,sys
import subprocess

def ip2int(address):
	c = [int(x) for x in address.split('.')]
	return (c[0]<<24) | (c[1]<<16) | (c[2]<<8) | c[3]

def programRoach(fpga, boffile, src_ip_start, src_port_start, fid_start, registers={}):
	print "Writing program"
	# TODO: Can't use this method on our ADCs. Must use adc16_init.rb.
	#fpga.progdev(boffile)
	
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
	#output.close()
	
	time.sleep(1)
	
	print "Setting network configuration"
	starting_ch = 1250
	stop_ch = 3650
	high_ch = 300
	
	dest_ip   = [ip2int("192.168.0.%i" % (17+i*16)) for i in range(8)]
	dest_port = [4001 + i for i in range(8)]
	# TODO: Check this! In prog_10gall.py the last two are switched!
	#         Need to ensure the order is matched in leda_reset_header
	dest_port[6], dest_port[7] = dest_port[7], dest_port[6]
	src_ip    = [ip2int("192.168.0.%i" % (src_ip_start+i)) for i in range(8)]
	src_port  = [src_port_start + i for i in range(8)]
	"""
	print "dst_ip"
	print '\n'.join([str(x&0xff) for x in dest_ip])
	print "dst_port"
	print '\n'.join([str(x) for x in dest_port])
	print "src_ip"
	print '\n'.join([str(x&0xff) for x in src_ip])
	print "src_port"
	print '\n'.join([str(x) for x in src_port])
	"""
	mac_base = (2<<40) + (2<<32)
	
	fpga.write_int('adc_rst',3)
	fpga.write_int('tenge_start_count',starting_ch)
	fpga.write_int('tenge_high_ch',high_ch)
	fpga.write_int('tenge_stop_count',stop_ch)
	fpga.write_int('fft_fft_shift',65535)
	
	for i in range(8):
		fpga.tap_start('gbe%i'%i,'tenge_gbe%i%i'%(i/4,i%4),
		               mac_base+src_ip[i],src_ip[i],src_port[i])
	time.sleep(1)
	sys.stdout.flush()
	for i in range(8):
		fpga.write_int('tenge_ips_ip%i'%(i+1),dest_ip[i])
	for i in range(8):
		fpga.write_int('tenge_ports_port%i'%(i+1),dest_port[i])
	for i in range(4):
		fpga.write_int('tenge_f%i_fid'%(i+1),i+fid_start)
	
	print 'programming ROACH complete'
	time.sleep(1)
	
	# TODO: Is this necessary/desired?
	print('Starting data flow...\n')
	fpga.write_int('tenge_enable',1)
	time.sleep(1)
	
	print "Writing gain coefficients"
	#odata = numpy.ones(4096,'l')*(1<<7)
	#odata = numpy.ones(4096,'l')*(700<<8)
	odata = numpy.ones(4096,'l')*(700<<7)
	cstr = struct.pack('>4096l',*odata)
	odata0 = numpy.zeros(4096,'l')
	cstr0 = struct.pack('>4096l',*odata0)
	for i in range(4):
		fpga.write('fft_f%i_coeffs' %(i+1),cstr)
		fpga.write('fft_f%i_coeffs1'%(i+1),cstr)

if __name__ == "__main__":
	roaches = ['169.254.128.14', '169.254.128.13']
	boffile = 'l64x8_06022013.bof'
	
	# TESTING Setting digital gain registers to 5x
	gain_reg     = 0x2a
	#gain_setting = 0x5555 # 5x
	gain_setting = 0x8888 # 8x
	#gain_setting = 0xCCCC # 12x
	registers = {gain_reg: gain_setting}
	#registers = {}
	
	print "Programming ROACH .14"
	print "---------------------"
	fpga  = corr.katcp_wrapper.FpgaClient(roaches[0], 7147)
	time.sleep(2)
	programRoach(fpga, boffile, src_ip_start=145, src_port_start=4010,
		     fid_start=0,
	             registers=registers)
		     
	print "Programming ROACH .13"
	print "---------------------"
	fpga  = corr.katcp_wrapper.FpgaClient(roaches[1], 7147)
	time.sleep(2)
	programRoach(fpga, boffile, src_ip_start=161, src_port_start=4020,
		     fid_start=4,
	             registers=registers)
	
	print "Waiting 3 minutes for ARP tables to update"
	time.sleep(180)
	
	print "Done"
