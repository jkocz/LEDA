#! /usr/bin/env python

#import pcorr
#import pylib,time,struct,sys,os,numpy
import corr,time,struct,sys,os,numpy

print( 'Writing gain coefficients\n')
roach     = '169.254.128.13'
fpga = corr.katcp_wrapper.FpgaClient(roach, 7147)
time.sleep(1)
#odata = numpy.ones(4096,'l')*(1<<7)
#odata = numpy.ones(4096,'l')*(700<<8)
odata = numpy.ones(4096,'l')*(700<<7)
cstr = struct.pack('>4096l',*odata)

odata0 = numpy.zeros(4096,'l')
cstr0 = struct.pack('>4096l',*odata0)
fpga.write('fft_f1_coeffs',cstr)
fpga.write('fft_f1_coeffs1',cstr)
fpga.write('fft_f2_coeffs',cstr)
fpga.write('fft_f2_coeffs1',cstr)
fpga.write('fft_f3_coeffs',cstr)
fpga.write('fft_f3_coeffs1',cstr)
fpga.write('fft_f4_coeffs',cstr)
fpga.write('fft_f4_coeffs1',cstr)
