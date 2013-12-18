#!/usr/bin/env python

"""

.) Read from xgpu output buffer
.) Convert to triangular baseline order
a) Extract, integrate and dump TP signals
b) Integrate (BDI) signals, write as FITSIDI
c) Integrate (fixed length) signals, write to transient buffer

"""

import numpy as np

#import sys
#sys.path.insert(0, "../dada/pysrdada")

from xgpu_reader import *

class SDFITSWriter(object):
	def __init__(self, filestem):
		self.filestem = filestem
		
	def write(self, data):
		pass

class FixedIntegrator(object):
	"""Accumulates navg data sets, storing up to nbuf averages in memory
	"""
	def __init__(self, navg, nbuf=1):
		self.navg  = navg
		self.nbuf  = nbuf
		self.data  = None
		self.avg   = 0
		self.buf   = 0
	def update(self, data):
		"""Adds data to the accumulation
		Returns all accumulation buffers if nbuf is reached, else None.
		"""
		if self.data == None:
			self.avg = 0
			self.buf = 0
			self.data = np.zeros((self.nbuf,) + data.shape, dtype=data.dtype)
		self.data[self.buf] += data
		self.avg += 1
		if self.avg == self.navg:
			self.avg  = 0
			self.buf += 1
			if self.buf == self.nbuf:
				# Return and reset all integrations
				self.buf = 0
				# TODO: Can re-order things to avoid need to copy? Too dangerous?
				dump_data = self.data.copy()
				self.data[...] = 0
				return dump_data
		return None
	def dump(self):
		"""Returns all full accumulation buffers and resets internal counters
		"""
		nbuf = self.buf
		self.avg = 0
		self.buf = 0
		return self.data[:nbuf]

class TotalPowerIntegrator(FixedIntegrator):
	"""Specialises FixedIntegrator to accumulate only the total power signals
	from a given set of stands.
	"""
	def __init__(self, stands, *args, **kwargs):
		super(TotalPowerIntegrator, self).__init__(*args, **kwargs)
		# Note: Stands given are assumed to use 1-based indexing
		self.stands = np.array(stands, dtype=np.int32) - 1
	def update(self, data):
		# Extract total power values before passing to super
		stands = self.stands
		# Note: data assumed to have shape (nbin, nbaseline, nchan, npol, npol)
		npol   = data.shape[-1]
		pols   = np.arange(npol)
		tpdata = data[:,bid(stands,stands),...][...,pols,pols].real
		return super(TotalPowerIntegrator, self).update(tpdata)

def ilog2(v):
	"""From http://stackoverflow.com/a/2259769
    Limit: v < 2**33
    """
	v = int(v)
	if v <= 0:
		raise ValueError("Invalid argument to logarithm")
	assert(v < (1<<33))
	r = 0
	if v > 0xffff:
		v >>= 16
		r = 16
	if v > 0x00ff:
		v >>=  8
		r += 8
	if v > 0x000f:
		v >>=  4
		r += 4
	if v > 0x0003:
		v >>=  2
		r += 2
	return r + (v >> 1)
def first_set_bit(x):
	x = int(x)
	"""Returns index of first set bit in integer x, or -1 if x==0"""
	return bin(x)[::-1].find('1')

class BDIIntegrator(object):
	def __init__(self, baseline_times, corr_dump_time,
	             maxdump=None, tol=0.01):
		
		# Compute dump maps
		mintime = np.min(baseline_times)
		maxtime = np.max(baseline_times)
		self.min_navg = int(mintime / corr_dump_time + tol)
		maxdump_ = ilog2(int(maxtime / mintime + tol))
		if maxdump is not None:
			maxdump = min(maxdump, maxdump_)
		else:
			maxdump = maxdump_
		self.dump_maps = [[] for _ in xrange(maxdump+1)]
		for bid, time in enumerate(baseline_times):
			dump = ilog2(int(time / mintime + tol))
			self.dump_maps[dump].append(bid)
		# Convert to numpy arrays
		self.dump_maps = [np.array(dm, dtype=np.int32) for dm in self.dump_maps]
		
		self.cycle_size = sum([dm.size * 2**(maxdump-i) \
			                       for (i,dm) in enumerate(self.dump_maps)])
		
	def update(self, data):
		if self.data is None:
			self.accum = zeros_like(data)
			baseline_size = data[:,0,...].size
			# TODO: How to manage baseline data when bin runs slower?
			self.data = np.zeros((self.ncycle,
			                      self.cycle_size*baseline_size),
			                     dtype=data.dtype)
			self.avg = 0
			self.interval = 0
			self.cycle_offset = 0
			self.cycle = 0
		
		self.accum += data
		self.avg += 1
		if self.avg == self.min_navg:
			self.avg = 0
			self.interval += 1
			dump = first_set_bit(self.interval)
			
			# This interval we dump from all maps <= dump
			dump_map = np.concatenate(self.dump_maps[:dump+1])
			# Extract and reset accumulations
			self.data[self.cycle,
			          self.cycle_offset:self.cycle_offset+dump_map.size] \
			    = self.accum[self.buf][:,dump_map,...]
			self.accum[self.buf][:,dump_map,...] = 0
			self.cycle_offset += dump_map.size
			
			if dump == len(self.dump_maps)-1:
				# This is the longest dump (i.e., end of a cycle), so reset
				#   counters for next time.
				self.interval = 0
				self.cycle_offset = 0
				self.cycle += 1
				if self.cycle == self.ncycle:
					self.cycle = 0
					return self.data
		return None

class SimpleBinaryWriter(object):
	def __init__(self, header, outstem, suffix=".dada",
	             max_filesize=2147483647, header_size=4096):
		self.header       = header
		self.outstem      = outstem
		self.byte_offset  = 0
		self.max_filesize = max_filesize
		self.header_size  = header_size
		self.suffix       = suffix
		self.file         = None
	def __del__(self):
		self.close()
	def open(self):
		self.close()
		filename = self.outstem + "_%016i%s" % (self.byte_offset,self.suffix)
		self.file = open(filename, 'wb')
		headerstr = serialize_header(self.header)
		if len(headerstr) > self.header_size:
			raise ValueError("Serialized header exceeds header size")
		self.file.write(headerstr)
		self.file.seek(self.header_size, 0)
	def close(self):
		if self.file is not None:
			self.file.close()
			self.file = None
	# Note: This method can be used alone, without needing to call open/close
	def write(self, data):
		if self.file is None:
			self.open()
		elif self.byte_offset + data.nbytes > self.max_filesize:
			self.open()
		data.tofile(self.file)
		self.byte_offset += data.nbytes
	def reset(self):
		self.byte_offset = 0
		self.close()

if __name__ == "__main__":
	import sys
	import os
	import argparse
	#from pysrdada import dada_handle
	#from pysrdada.pysrdada import dada_handle
	from pysrdada.pysrdada2 import *
	import numpy as np
	import time
	
	parser = argparse.ArgumentParser(description="LEDA post-correlation processor")
	parser.add_argument("in_key", help="psrdada buffer key to read from")
	#parser.add_argument("out_key", help="psrdada buffer key to write pass-through data to")
	parser.add_argument("-tp", "--totalpower", action="store_true",
	                    help="Enable total power recording")
	parser.add_argument("-corr", "--correlator", action="store_true",
	                    help="Enable correlator recording")
	parser.add_argument("-bdi", "--bdi", action="store_true",
	                    help="Enable baseline-dependent integrations for correlator (BDI)")
	#parser.add_argument("-ts", "--transients", action="store_true",
	#                    help="Enable transient search output")
	parser.add_argument("-trkey", "--transients_key",
	                    help="psrdada buffer key to write transients data to")
	parser.add_argument("-o", "--outpath", required=True,
	                    help="Path where output files should be written")
	parser.add_argument("-core", "--core", type=int,
	                    help="CPU core to bind process to")
	parser.add_argument('--verbose', '-v', action='count', default=0,
	                    help="Increase verbosity")
	parser.add_argument('--quiet', '-q', action='count', default=0,
	                    help="Decrease verbosity")
	
	args = parser.parse_args()
	
	log = MultiLog("leda_dbpost")
	log.add(sys.stderr)
	log.verbosity += args.verbose - args.quiet
	
	if args.core is not None:
		log.notice("Binding thread to core %i" % args.core)
		bind_thread_to_core(args.core)
	else:
		log.notice("Not binding thread to any particular core")
	
	log.info("Creating Dada HDU object")
	#inbuf = dada_handle("leda_dbpost")
	inbuf = DadaHDU(log)
	log.info("Connecting to input buffer '%s'" % (args.in_key,))
	inbuf.set_key(args.in_key)
	inbuf.connect()
	log.info("Locking input buffer for read")
	inbuf.lock_read()
	log.notice("Waiting to open header")
	inbuf.open()
	
	log.info("Reading header from input buffer")
	#headerstr = inbuf.read_header()
	header = parse_header(inbuf.header)
	
	log.info("Creating XGPUReader")
	xgpu_reader = XGPUReader(header)
	npol = xgpu_reader.npol
	
	#npol = int(inbuf.header['NPOL'])
	utc_start = header['UTC_START']
	outstem = os.path.join(args.outpath, utc_start)
	log.info("Output stem set to %s" % (outstem,))
	
	tp_integrator        = None
	corr_integrator      = None
	transient_integrator = None
	
	if args.totalpower:
		log.notice("Total power recording enabled")
		tpheader = header.copy()
		tpheader["DATA_ORDER"] = "time_state_bin_station_chan_pol"
		tp_writer = SimpleBinaryWriter(tpheader, outstem, suffix=".tp",
		                               max_filesize=(128*1024*1024))
		#tp_writer = SDFITSWriter( )
		tp_integrator = TotalPowerIntegrator(stands=[252,253,254,255,256],
		                                     #navg=3, nbuf=60)
		                                     #navg=3, nbuf=3)
		                                     navg=1, nbuf=3)
		
	#if args.correlator:
	#	print "leda_dbpost: Correlator recording enabled"
	#	if args.bdi:
	#		corr_integrator = BDIIntegrator( )
	#	else:
	#		corr_integrator = FixedIntegrator( )
	
	#if args.transients_key:
	#	print "leda_dbpost: Transients output enabled"
	#	transient_integrator = FixedIntegrator(navg=3)
	#	transient_buf = dada_handle("leda_dbpost_transient")
	#	transient_buf.connect(args.transients_key)
	#	transient_buf.lock_write()
	
	log.info("Allocating raw input buffer")
	#rawdata = create_string_buffer(inbuf.data_block.bufsz)
	rawdata = np.zeros(inbuf.data_block.bufsz, dtype=np.uint8)
	log.info("Entering pipeline loop")
	#while not inbuf.eod:
	log.notice("Waiting to read from input buffer")
	while inbuf.data_block.read(rawdata):
		#rawdata = inbuf.read_buffer()
		log.info("Converting raw data")
		start_time = time.time()
		data = xgpu_reader.process(rawdata)
		run_time = time.time() - start_time
		log.debug("  Time = %f s" % run_time)
		log.debug("       = %f Hz" % (1./run_time,))
		
		#if transient_integrator is not None:
		#	transient_data = transient_integrator.update(data)
		#	if transient_data is not None:
		#		transient_buf.write(transient_data)
		
		if tp_integrator is not None:
			log.notice("Updating total power integrator")
			tp_data = tp_integrator.update(data)
			if tp_data is not None:
				log.notice("Writing total power integrations")
				tp_writer.write(tp_data)
		
		#if corr_integrator is not None:
		#	corr_data = corr_integrator.update(data)
		#	if corr_data is not None:
		#		corr_writer.write(corr_data)
		
		"""
		if args.totalpower:
			## is_switching = bool(header['SWITCHING'])
			# state0 = int(header['FIRST_SWITCH_STATE'])
			# tp_stands = [252, 253, 254, 255, 256]
			pols = np.arange(npol)
			tp_data = data[:,bid(tp_stands,tp_stands),...][...,pols,pols].real
			tp_outfile.write(tp_data)
		"""
		log.notice("Waiting to read from input buffer")
		
	log.notice("EOD reached")
	log.info("Disconnecting from input buffer")
	inbuf.disconnect()
	log.notice("All done, exiting")
