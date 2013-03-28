#! /usr/bin/env python

#import pcorr
#import pylib,time,struct,sys,os,numpy
import corr,time,struct,sys,os,numpy

print( 'Writing gain coefficients\n')
roach1     = '192.168.0.5'
fpga1 = corr.katcp_wrapper.FpgaClient(roach1, 7147)
time.sleep(1)
roach2     = '192.168.0.4'
fpga2 = corr.katcp_wrapper.FpgaClient(roach2, 7147)
time.sleep(1)
roach3     = '192.168.0.3'
fpga3 = corr.katcp_wrapper.FpgaClient(roach3, 7147)
time.sleep(1)
roach4     = '192.168.0.6'
fpga4 = corr.katcp_wrapper.FpgaClient(roach4, 7147)
time.sleep(2)

#odata = numpy.ones(4096,'l')*(1<<7)
#odata = numpy.ones(4096,'l')*(700<<8)
odata = numpy.ones(4096,'l')*(700<<7)
cstr = struct.pack('>4096l',*odata)

odata0 = numpy.zeros(4096,'l')
cstr0 = struct.pack('>4096l',*odata0)

fpga1.write('fft_clip_eq0_coeffs',cstr)
fpga1.write('fft_clip_eq1_coeffs',cstr)
fpga1.write('fft_clip_eq2_coeffs',cstr)
fpga1.write('fft_clip_eq3_coeffs',cstr)
fpga1.write('fft_clip_eq4_coeffs',cstr)
fpga1.write('fft_clip_eq5_coeffs',cstr)
fpga1.write('fft_clip_eq6_coeffs',cstr)
fpga1.write('fft_clip_eq7_coeffs',cstr)

fpga2.write('fft_clip_eq0_coeffs',cstr)
fpga2.write('fft_clip_eq1_coeffs',cstr)
fpga2.write('fft_clip_eq2_coeffs',cstr)
fpga2.write('fft_clip_eq3_coeffs',cstr)
fpga2.write('fft_clip_eq4_coeffs',cstr)
fpga2.write('fft_clip_eq5_coeffs',cstr)
fpga2.write('fft_clip_eq6_coeffs',cstr)
fpga2.write('fft_clip_eq7_coeffs',cstr)

fpga3.write('fft_clip_eq0_coeffs',cstr)
fpga3.write('fft_clip_eq1_coeffs',cstr)
fpga3.write('fft_clip_eq2_coeffs',cstr)
fpga3.write('fft_clip_eq3_coeffs',cstr)
fpga3.write('fft_clip_eq4_coeffs',cstr)
fpga3.write('fft_clip_eq5_coeffs',cstr)
fpga3.write('fft_clip_eq6_coeffs',cstr)
fpga3.write('fft_clip_eq7_coeffs',cstr)

fpga4.write('fft_clip_eq0_coeffs',cstr)
fpga4.write('fft_clip_eq1_coeffs',cstr)
fpga4.write('fft_clip_eq2_coeffs',cstr)
fpga4.write('fft_clip_eq3_coeffs',cstr)
fpga4.write('fft_clip_eq4_coeffs',cstr)
fpga4.write('fft_clip_eq5_coeffs',cstr)
fpga4.write('fft_clip_eq6_coeffs',cstr)
fpga4.write('fft_clip_eq7_coeffs',cstr)

# o1 = struct.unpack('>4096l', fpga4.read('fft_clip_eq0_coeffs',4096*4,0))

