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
roach10     = 'rofl10'
roach11     = 'rofl11'
roach12     = 'rofl12'
roach13     = 'rofl13'
roach14     = 'rofl14'
roach15     = 'rofl15'
roach16     = 'rofl16'



fpga1 = corr.katcp_wrapper.FpgaClient(roach1, 7147)
#fpga2 = corr.katcp_wrapper.FpgaClient(roach2, 7147)
fpga3 = corr.katcp_wrapper.FpgaClient(roach3, 7147)
fpga4 = corr.katcp_wrapper.FpgaClient(roach4, 7147)
#fpga5 = corr.katcp_wrapper.FpgaClient(roach5, 7147)
fpga6 = corr.katcp_wrapper.FpgaClient(roach6, 7147)
fpga7 = corr.katcp_wrapper.FpgaClient(roach7, 7147)
fpga8 = corr.katcp_wrapper.FpgaClient(roach8, 7147)
fpga9 = corr.katcp_wrapper.FpgaClient(roach9, 7147)
fpga10 = corr.katcp_wrapper.FpgaClient(roach10, 7147)
fpga11 = corr.katcp_wrapper.FpgaClient(roach11, 7147)
#fpga12 = corr.katcp_wrapper.FpgaClient(roach12, 7147)
fpga13 = corr.katcp_wrapper.FpgaClient(roach13, 7147)
fpga14 = corr.katcp_wrapper.FpgaClient(roach14, 7147)
#fpga15 = corr.katcp_wrapper.FpgaClient(roach15, 7147)
#fpga16 = corr.katcp_wrapper.FpgaClient(roach16, 7147)

time.sleep(1)

print '------------------------\n'
print 'Resetting counter...\n',
fpga1.write_int('tenge_enable', 0)
#fpga2.write_int('tenge_enable', 0)
fpga3.write_int('tenge_enable', 0)
fpga4.write_int('tenge_enable', 0)
#fpga5.write_int('tenge_enable', 0)
fpga6.write_int('tenge_enable', 0)
fpga7.write_int('tenge_enable', 0)
fpga8.write_int('tenge_enable', 0)
fpga9.write_int('tenge_enable', 0)
fpga10.write_int('tenge_enable', 0)
fpga11.write_int('tenge_enable', 0)
#fpga12.write_int('tenge_enable', 0)
fpga13.write_int('tenge_enable', 0)
fpga14.write_int('tenge_enable', 0)
#fpga15.write_int('tenge_enable', 0)
#fpga16.write_int('tenge_enable', 0)

print 'done\n'
