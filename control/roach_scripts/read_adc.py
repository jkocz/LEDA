#!/usr/bin/env python
import corr,time,numpy,struct,sys,matplotlib,pylab,math

#fpga4 = corr.katcp_wrapper.FpgaClient('192.168.0.6',7147)
fpga4 = corr.katcp_wrapper.FpgaClient('169.254.128.13',7147)
time.sleep(2)
#out_adc = struct.unpack('>16384l',fpga4.read('sn_dataram',16384*4,0))
fpga4.write_int('adc_sub_sn_ctrl',1)
time.sleep(1)
fpga4.write_int('adc_sub_sn_ctrl',0)
numPoints = 1024

out_adc = struct.unpack('>4096b',fpga4.read('adc_sub_sn_dataram',1024*4,0))
j=0
i=0
out4 = numpy.zeros(numPoints,'b')
out3 = numpy.zeros(numPoints,'b')
out2 = numpy.zeros(numPoints,'b')
out1 = numpy.zeros(numPoints,'b')
while (i < 4096):
	out1[j] = out_adc[i]
        i=i+1;
        out2[j] = out_adc[i]
        i=i+1;
	out3[j] = out_adc[i]
	i=i+1;
	out4[j] = out_adc[i]
	i=i+1;
	j=j+1;


fig = pylab.figure()

dpi = fig.get_dpi()
default_size = fig.get_size_inches()
xdim = dpi*default_size[0]

ax = fig.add_subplot(2,2,1)
ax.set_title('ADC bits - 4 inputs')
ax.set_xlabel('Time')
ax.set_ylabel('Bits')
ax.grid(False)

ax.plot(out1,'-')

ax = fig.add_subplot(2,2,2)
ax.plot(out2,'-')
ax = fig.add_subplot(2,2,3)
ax.plot(out3,'-')
ax = fig.add_subplot(2,2,4)
ax.plot(out4,'-')

matplotlib.pylab.show()

#out_adc = struct.unpack('>16384l',fpga4.read('sn_dataram',16384*4,0))
#j=0
#i=0
#out4 = numpy.zeros(16384,'b')
#out3 = numpy.zeros(16384,'b')
#out2 = numpy.zeros(16384,'b')
#out1 = numpy.zeros(16384,'b')
#while (i < 16384):
#        out1[j] = (out_adc[i]  >>24) #& 0xf000) >> 24)
#        out2[j] = (out_adc[i]  >>16) #& 0x0f00) >>16)
#        out3[j] = (out_adc[i]  >> 8) #& 0x00f0) >> 8)
#        out4[j] = (out_adc[i]  >> 0) #& 0x000f) >> 0)
#        i=i+1
#        j=j+1


#fig1 = pylab.figure(2)

#dpi = fig1.get_dpi()
#default_size = fig1.get_size_inches()
#xdim = dpi*default_size[0]
#
#ax2 = fig1.add_subplot(2,2,1)
#ax2.set_title('ADC bits - 4 inputs groups of 32')
#ax2.set_xlabel('Time')#
#ax2.set_ylabel('Bits')
#ax2.grid(False)

#ax2.plot(out1,'-')

#ax2 = fig1.add_subplot(2,2,2)
#ax2.plot(out2,'-')
#ax2 = fig1.add_subplot(2,2,3)
#ax2.plot(out3,'-')
#ax2 = fig1.add_subplot(2,2,4)
#ax2.plot(out4,'-')

#matplotlib.pylab.show()
