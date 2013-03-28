#!/usr/bin/env python
import corr,time,numpy,struct,sys,matplotlib,pylab,math

f1 = open('./adc1_readout1','w');
f2 = open('./adc1_readout2','w');
f3 = open('./adc1_readout3','w');
f4 = open('./adc1_readout4','w');
f5 = open('./adc1_readout5','w');
f6 = open('./adc1_readout6','w');
f7 = open('./adc1_readout7','w');
f8 = open('./adc1_readout8','w');

f1b = open('./adc2_readout1','w');
f2b = open('./adc2_readout2','w');
f3b = open('./adc2_readout3','w');
f4b = open('./adc2_readout4','w');
f5b = open('./adc2_readout5','w');
f6b = open('./adc2_readout6','w');
f7b = open('./adc2_readout7','w');
f8b = open('./adc2_readout8','w');

f1c = open('./adc3_readout1','w');
f2c = open('./adc3_readout2','w');
f3c = open('./adc3_readout3','w');
f4c = open('./adc3_readout4','w');
f5c = open('./adc3_readout5','w');
f6c = open('./adc3_readout6','w');
f7c = open('./adc3_readout7','w');
f8c = open('./adc3_readout8','w');

f1d = open('./adc4_readout1','w');
f2d = open('./adc4_readout2','w');
f3d = open('./adc4_readout3','w');
f4d = open('./adc4_readout4','w');
f5d = open('./adc4_readout5','w');
f6d = open('./adc4_readout6','w');
f7d = open('./adc4_readout7','w');
f8d = open('./adc4_readout8','w');



fpga1 = corr.katcp_wrapper.FpgaClient('192.168.0.5',7147)
fpga2 = corr.katcp_wrapper.FpgaClient('192.168.0.4',7147)
fpga3 = corr.katcp_wrapper.FpgaClient('192.168.0.3',7147)
fpga4 = corr.katcp_wrapper.FpgaClient('192.168.0.6',7147)
time.sleep(2)
#out_adc = struct.unpack('>16384l',fpga4.read('sn_dataram',16384*4,0))
j=0;

numPoints = 65536

while (j < 50):
	fpga1.write_int('sn_ctrl',1)
	fpga1.write_int('sn1_ctrl',1)
	fpga2.write_int('sn_ctrl',1)
	fpga2.write_int('sn1_ctrl',1)
	fpga3.write_int('sn_ctrl',1)
	fpga3.write_int('sn1_ctrl',1)
	fpga4.write_int('sn_ctrl',1)
	fpga4.write_int('sn1_ctrl',1)
	time.sleep(2)
	fpga1.write_int('sn_ctrl',0)
	fpga1.write_int('sn1_ctrl',0)
	fpga2.write_int('sn_ctrl',0)
	fpga2.write_int('sn1_ctrl',0)
	fpga3.write_int('sn_ctrl',0)
	fpga3.write_int('sn1_ctrl',0)
	fpga4.write_int('sn_ctrl',0)
	fpga4.write_int('sn1_ctrl',0)

	out_adc1 = struct.unpack('>262144b',fpga1.read('sn_dataram',65536*4,0))
	out_adc11 = struct.unpack('>262144b',fpga1.read('sn1_dataram',65536*4,0))
	out_adc2 = struct.unpack('>262144b',fpga2.read('sn_dataram',65536*4,0))
	out_adc21 = struct.unpack('>262144b',fpga2.read('sn1_dataram',65536*4,0))
	out_adc3 = struct.unpack('>262144b',fpga3.read('sn_dataram',65536*4,0))
	out_adc31 = struct.unpack('>262144b',fpga3.read('sn1_dataram',65536*4,0))
	out_adc4 = struct.unpack('>262144b',fpga4.read('sn_dataram',65536*4,0))
	out_adc41 = struct.unpack('>262144b',fpga4.read('sn1_dataram',65536*4,0))
	
	i=0
	while (i < 262144):
		f1.write("%d\n" %out_adc1[i])
		f1b.write("%d\n" %out_adc2[i])
		f1c.write("%d\n" %out_adc3[i])
		f1d.write("%d\n" %out_adc4[i])
		f5.write("%d\n" %out_adc11[i])
		f5b.write("%d\n" %out_adc21[i])
		f5c.write("%d\n" %out_adc31[i])
		f5d.write("%d\n" %out_adc41[i])
	        i=i+1;
		f2.write("%d\n" %out_adc1[i])
		f2b.write("%d\n" %out_adc2[i])
		f2c.write("%d\n" %out_adc3[i])
		f2d.write("%d\n" %out_adc4[i])
		f6.write("%d\n" %out_adc11[i])
		f6b.write("%d\n" %out_adc21[i])
		f6c.write("%d\n" %out_adc31[i])
		f6d.write("%d\n" %out_adc41[i])
	        i=i+1;
		f3.write("%d\n" %out_adc1[i])
		f3b.write("%d\n" %out_adc2[i])
		f3c.write("%d\n" %out_adc3[i])
		f3d.write("%d\n" %out_adc4[i])
		f7.write("%d\n" %out_adc11[i])
		f7b.write("%d\n" %out_adc21[i])
		f7c.write("%d\n" %out_adc31[i])
		f7d.write("%d\n" %out_adc41[i])
		i=i+1;
		f4.write("%d\n" %out_adc1[i])
		f4b.write("%d\n" %out_adc2[i])
		f4c.write("%d\n" %out_adc3[i])
		f4d.write("%d\n" %out_adc4[i])
		f8.write("%d\n" %out_adc11[i])
		f8b.write("%d\n" %out_adc21[i])
		f8c.write("%d\n" %out_adc31[i])
		f8d.write("%d\n" %out_adc41[i])
		i=i+1;
	j=j+1;

