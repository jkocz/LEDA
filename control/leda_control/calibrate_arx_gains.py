#!/usr/bin/env python

"""

TODO: Allow AT2 values to be ideal DB gains as floats
        Allowable ARX values + residuals then derived from these
      Fully automate the generation of this file via a 'calibrate_arx' script
      
      ./calibrate_arx_gains.py -g rms -w
"""

import subprocess
import time
import numpy as np

def get_adc_samples(roach):
	nstands = 16
	npols   = 2
	nsamps  = 1024
	#return 40 * np.random.standard_normal((nsamps, nstands, npols))
	sp = subprocess.Popen(["adc16_dump_chans.rb", "-l", str(nsamps), roach],
	                      stdout=subprocess.PIPE)
	out, err = sp.communicate()
	if len(out) < 1024:
		print "ERROR adc16_dump_chans.rb output:\n---"
		print out
		print "---"
	data = np.fromstring(out, sep=' ', dtype='int')
	try:
		data = data.reshape(nsamps, nstands, npols)
	except ValueError:
		return None
	return data

class ARXCal(object):
	def __init__(self):
		self.ATS = 30
		self.bad_thresh = 4.0
		self.nrepeat    = 10
		self.sleeptime  = 1.0
		nroach          = 16
		self.roaches    = ['rofl%i' % (i+1) for i in xrange(nroach)]
		
	def load(self, filename):
		self.AT1 = 0
		self.AT2 = {}
		self.bad_stands  = []
		self.semi_stands = []
		execfile(filename, self.__dict__)
		
	def save(self, filename):
		f = open(filename, 'w')
		f.write("bad_stands = [%s]\n" \
			        % ", ".join([str(x) for x in self.bad_stands]))
		f.write("\n")
		f.write("semi_stands = [%s]\n" \
			        % ", ".join([str(x) for x in self.semi_stands]))
		f.write("\n")
		f.write("AT1 = %.3f\n" % self.AT1)
		f.write("\n")
		for key, val in self.AT2.items():
			f.write("AT2[%3i] = %.3f\n" % (key, val))
		f.close()
		
	def _get_nearest_atten(self, val):
		return int(val / 2. + 0.5) * 2
	def _get_residual_atten(self, val):
		return val - self._get_nearest_atten(val)
	
	def prettyprint(self):
		ncols = 8
		print "# AT1 = %i dB" % (self.AT1)
		print
		print "# AT2 [dB]"
		for j in xrange(len(self.AT2)/ncols):
			line = ""
			for i in xrange(ncols):
				idx = i + j*ncols
				val = self._get_nearest_atten(self.AT2[idx+1])
				line += "%02i " % (val)
			print line
		print
		print "# Residuals [dB]"
		for j in xrange(len(self.AT2)/ncols):
			line = ""
			for i in xrange(ncols):
				idx = i + j*ncols
				val = self._get_residual_atten(self.AT2[idx+1])
				line += "%+.3f " % (val)
			print line
			
		print
		print "# Bad stands"
		line = ""
		for stand in self.bad_stands:
			line += "%i " % (stand)
		print line
		
		print
		print "# Semi-bad stands"
		line = ""
		for stand in self.semi_stands:
			line += "%i " % (stand)
		print line
	
	def calibrate(self, target_rms):
		print "Computing updated ARX calibration"
		
		async = AsyncCaller()
		stddevs = []
		for t in xrange(self.nrepeat):
			print "  Sampling ADC inputs (rep %i)" % (t+1)
			for roach in self.roaches:
				async(get_adc_samples)(roach)
			roach_samples = async.wait()
			if None in roach_samples:
				raise ValueError("One or more ADC reads failed")
			samples = np.hstack(roach_samples)
			stddevs.append(samples.std(axis=0))
			time.sleep(self.sleeptime)
		stddevs = np.array(stddevs)
		# Note: Shape is (nrepeat,nstands,npols)
		
		# Compute median of repetitions
		stddevs = np.median(stddevs, axis=0)
		
		# Find and deal with bad stands and pols
		self.bad_stands  = []
		self.semi_stands = []
		typical = np.median(stddevs) # Median of all inputs
		for i in xrange(stddevs.shape[0]):
			polA_bad = stddevs[i][0] < self.bad_thresh
			polB_bad = stddevs[i][1] < self.bad_thresh
			if polA_bad and polB_bad:
				self.bad_stands.append(i+1)
				stddevs[i][0] = stddevs[i][1] = typical
			elif polA_bad:
				self.semi_stands.append(i+1)
				stddevs[i][0] = stddevs[i][1]
			elif polB_bad:
				self.semi_stands.append(i+1)
				stddevs[i][1] = stddevs[i][0]
				
		# Average the two pols (as there is no per-pol ARX gain control)
		stddevs = stddevs.mean(axis=1)
		
		# Update the attenuation values
		for i, x in enumerate(stddevs):
			delta_atten = 10*math.log10(x / target_rms)
			self.AT2[i+1] += delta_atten
	
	def apply(self):
		rabbit_ips  = ["192.168.25.2", "192.168.25.4", "192.168.25.5", "192.168.25.6"]
		rabbit_port = 1738
		for rabbit_ip in rabbit_ips:
			print "Applying gain settings via Rabbit at %s" % (rabbit_ip,)
			asp = AspController(boards=8,
			                    txAddr=(rabbit_ip, rabbit_port),
			                    timeout=5,
			                    verbose=False)
			asp.shutdown()
			asp.initialize()
			asp.setFilter(asp.splitFilter)
			asp.setAT1(self.AT1)
			asp.setATS(self.ATS)
			for stand in xrange(1, 65):
				atten = self._get_nearest_atten(self.AT2[stand])
				asp.setAT2(atten if stand in self.AT2 else 0, stand)
				asp.powerFEE(stand not in self.bad_stands, stand = stand)
			asp.close()
	
if __name__ == "__main__":
	from async import AsyncCaller
	import math
	import sys
	
	generate = False
	save     = False
	applycal = False
	
	if len(sys.argv) <= 1 or '-h' in sys.argv or '--help' in sys.argv:
		print "Usage:", sys.argv[0], "[options] arx_cal_file"
		print "Options:"
		print "  -c target_rms    Generate calibration"
		print "  -s               Save calibration"
		print "  -a               Apply calibration"
		print "  -h/--help        Print this usage info"
		sys.exit(-1)
		
	calfile = sys.argv[-1]
	
	i = 1
	while i < len(sys.argv)-1:
		arg = sys.argv[i]
		if arg == '-c':
			generate = True
			i += 1
			target_rms = float(sys.argv[i])
		elif arg == '-s':
			save = True
		elif arg == '-a':
			applycal = True
		else:
			print "Unrecognised argument '%s'" % arg
		i += 1
	
	cal = ARXCal()
	cal.load(calfile)
	
	if generate:
		try:
			cal.calibrate(target_rms)
		except ValueError:
			print "Calibration FAILED due to ADC error; try again later"
			sys.exit(-1)
	if save:
		cal.save(calfile)
	if applycal:
		cal.apply()
		
	cal.prettyprint()
	
	sys.exit(0)
	
"""

#AT2[1] = 2
#AT2[2] = 2
#AT2[3] = 
#AT2[4] = 
attens = {1:2,  2:2,  3:4,  4:4,  5:4,  6:4,  7:4,  8:6,
              9:4, 10:4, 11:6, 12:6, 13:8, 14:4, 15:6, 16:6,
             17:6, 18:4, 19:6, 20:8, 21:8, 22:8, 23:8, 24:6,
             25:8, 26:8, 27:8, 28:8, 29:8, 30:8, 31:8, 32:8,
             33:2, 34:4, 35:2, 36:2, 37:2, 38:2, 39:4, 40:4,
             41:4, 42:4, 43:8, 44:6, 45:4, 46:4, 47:6, 48:8,
             49:8, 50:6, 51:6, 52:8, 53:8, 54:8, 55:10, 56:10,
             57:10, 58:10, 59:10, 60:10, 61:10, 62:12, 63:10, 64:10}
key_offset = 0*64
val_offset = 0
for key, val in attens.items():
	print "AT2[%03i] = %i" % (key,val)

attens = {1:0,  2:0,  3:0,  4:0,  5:0,  6:0,  7:0,  8:0,
              9:2, 10:2, 11:6, 12:4, 13:4, 14:4, 15:4, 16:2,
             17:8, 18:8, 19:8, 20:8, 21:8, 22:8, 23:8, 24:8,
             25:8, 26:8, 27:10, 28:10, 29:10, 30:10, 31:8, 32:10,
             33:0, 34:0, 35:2, 36:2, 37:2, 38:4, 39:2, 40:2,
             41:4, 42:4, 43:4, 44:4, 45:4, 46:4, 47:4, 48:6,
             49:8, 50:6, 51:6, 52:8, 53:6, 54:4, 55:6, 56:6,
             57:8, 58:6, 59:8, 60:10, 61:8, 62:8, 63:10, 64:10}
key_offset = 1*64
val_offset = 4
for key, val in attens.items():
	print "AT2[%03i] = %i" % (key+key_offset,val+val_offset)

attens = {1:0,  2:0,  3:2,  4:0,  5:2,  6:2,  7:0,  8:2,
              9:2, 10:2, 11:2, 12:4, 13:2, 14:6, 15:4, 16:2,
             17:6, 18:6, 19:4, 20:4, 21:4, 22:6, 23:6, 24:6,
	     25:6, 26:8, 27:8, 28:8, 29:10, 30:10, 31:8, 32:10,
             33:0, 34:2, 35:0, 36:0, 37:0, 38:2, 39:0, 40:2,
             41:2, 42:4, 43:4, 44:2, 45:2, 46:4, 47:4, 48:4,
             49:6, 50:4, 51:6, 52:8, 53:6, 54:6, 55:6, 56:6,
             57:8, 58:6, 59:8, 60:8, 61:8, 62:8, 63:10, 64:10}
key_offset = 2*64
val_offset = 4
for key, val in attens.items():
	print "AT2[%03i] = %i" % (key+key_offset,val+val_offset)

attens = {1:0,  2:0,  3:0,  4:0,  5:0,  6:0,  7:0,  8:2,
              9:2, 10:2, 11:2, 12:2, 13:2, 14:2, 15:4, 16:4,
             17:6, 18:6, 19:4, 20:6, 21:2, 22:6, 23:6, 24:4,
	     25:8, 26:8, 27:8, 28:10, 29:8, 30:8, 31:8, 32:10,
             33:0, 34:2, 35:0, 36:2, 37:0, 38:2, 39:0, 40:4,
             41:4, 42:4, 43:4, 44:4, 45:4, 46:0, 47:4, 48:4,
             49:6, 50:6, 51:6, 52:6, 53:6, 54:6, 55:6, 56:6,
             57:8, 58:6, 59:8, 60:2, 61:0, 62:0, 63:4, 64:4}
key_offset = 3*64
val_offset = 2
for key, val in attens.items():
	print "AT2[%03i] = %i" % (key+key_offset,val+val_offset)
"""
