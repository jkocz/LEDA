#!/usr/bin/env python

import corr,time,numpy,struct,sys

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

fpga1.write_int('adc_rst',0)
fpga2.write_int('adc_rst',0)

print('Starting data flow...\n')
