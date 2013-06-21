#!/usr/bin/env python

import corr,time,numpy,struct,sys

roach1     = 'roach2-l1'
roach2     = 'roach2-l2'

fpga1 = corr.katcp_wrapper.FpgaClient(roach1, 7147)
fpga2 = corr.katcp_wrapper.FpgaClient(roach2, 7147)

time.sleep(1)

print '------------------------\n'
print 'Resetting counter...\n',
fpga1.write_int('tenge_enable', 0)
fpga1.write_int('adc_rst', 3)
fpga1.write_int('adc_rst', 0)

fpga2.write_int('tenge_enable', 0)
fpga2.write_int('adc_rst', 3)
fpga2.write_int('adc_rst', 0)
print '------------------------\n'
print 'Setting Enable...\n',
fpga1.write_int('tenge_enable', 1)
fpga2.write_int('tenge_enable', 1)

print 'done\n'
