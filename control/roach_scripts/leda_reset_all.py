#!/usr/bin/env python

import os,corr,time,numpy,struct,sys

roach1     = '169.254.128.13'
roach2     = '169.254.128.14'
fpga1 = corr.katcp_wrapper.FpgaClient(roach1, 7147)
fpga2 = corr.katcp_wrapper.FpgaClient(roach2, 7147)
time.sleep(2)

#boffile = 'l64x8_06022013.bof'
#fpga.progdev(boffile)

time.sleep(1)
fpga1.write_int('adc_rst',3)
fpga2.write_int('adc_rst',3)

fpga1.write_int('tenge_enable',1)
fpga2.write_int('tenge_enable',1)

print('Starting data flow...\n')
os.system('/home/leda/roach_scripts/leda_reset_header.sh')

time.sleep(10)
fpga1.write_int('adc_rst',0)
fpga2.write_int('adc_rst',0)
print 'enable done\n'

#print ' *** OBSERVATION COMPLETE ***\n'
# create port for udpdb
# open socket to port
# send header over socket
# send start command
# enable roach
# send UTC_START to socket
# set_utc_start YYYY-MM-DD-HH:MM:SS
