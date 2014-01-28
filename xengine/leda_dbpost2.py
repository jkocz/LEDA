#!/usr/bin/env python

"""

.) Read from xgpu output buffer
.) Convert to triangular baseline order
a) Extract, integrate and dump TP signals
b) Integrate (BDI) signals, write as FITSIDI
c) Integrate (fixed length) signals, write to transient buffer

"""

import numpy as np
import datetime
from xgpu_reader import *

def _cast_to_type(string):
	try: return int(string)
	except ValueError: pass
	try: return float(string)
	except ValueError: pass
	return string
def parse_header(headerstr, cast_types=True):
	header = {}
	for line in headerstr.split('\n'):
		try:
			key, value = line.split()
		except ValueError:
			break
		key = key.strip()
		value = value.strip()
		if cast_types:
			value = _cast_to_type(value)
		header[key] = value
	return header
def serialize_header(headerdict, keypadding=32):
	return '\n'.join([str(key).ljust(keypadding-1)+" "+str(val) \
		                  for (key,val) in headerdict.items()]) + '\n'

# Note: This is a Python version (not wrapper!) of the psrdada object
class MultiLog(object):
	# Note: These come from sys/syslog.h
	LOG_EMERG   = 0	# system is unusable
	LOG_ALERT   = 1	# action must be taken immediately
	LOG_CRIT    = 2	# critical conditions
	LOG_ERR     = 3	# error conditions
	LOG_WARNING = 4	# warning conditions
	LOG_NOTICE  = 5	# normal but significant condition
	LOG_INFO    = 6	# informational
	LOG_DEBUG   = 7	# debug-level messages
	def __init__(self, name):
		self.name = name
		self.verbosity = self.LOG_NOTICE
		self.files = []
	def add(self, fileobj):
		self.files.append(fileobj)
	def __call__(self, msg, priority):
		if priority > self.verbosity:
			return
		if not isinstance(msg, basestring):
			msg = str(msg)
		if priority == MultiLog.LOG_EMERG:
			msg = "EMERGENCY: " + msg
		elif priority == MultiLog.LOG_ALERT:
			msg = "ALERT: " + msg
		elif priority == MultiLog.LOG_CRIT:
			msg = "CRITICAL: " + msg
		elif priority == MultiLog.LOG_ERR:
			msg = "ERROR: " + msg
		elif priority == MultiLog.LOG_WARNING:
			msg = "WARNING: " + msg
		utc = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
		msg = "["+utc+"] " + msg + "\n"
		for f in self.files:
			f.write(msg)
			f.flush()
	def error(self, msg):
		return self.__call__(msg, self.LOG_ERR)
	def warning(self, msg):
		return self.__call__(msg, self.LOG_WARNING)
	def notice(self, msg):
		return self.__call__(msg, self.LOG_NOTICE)
	def info(self, msg):
		return self.__call__(msg, self.LOG_INFO)
	def debug(self, msg):
		return self.__call__(msg, self.LOG_DEBUG)

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

class SwitchingVisIntegrator(FixedIntegrator):
	"""Specialises FixedIntegrator to zero out the off-sky switching states
	from a given set of stands/baselines.
	
	TODO: This is written very specifically for the LEDA switching pipeline
	"""
	STATE_SKY = 0
	def __init__(self, switching_stands, initial_state=STATE_SKY, nstates=3,
	             *args, **kwargs):
		super(TotalPowerIntegrator, self).__init__(*args, **kwargs)
		# Note: Stands given are assumed to use 1-based indexing
		self.stands = np.array(stands, dtype=np.int32) - 1
		
		# Find all baseline IDs involving a switching stand
		self.switching_bids = np.zeros(0, dtype=np.int32)
		for stand in switching_stands:
			bids = np.concatenate([bid(stand, np.arange(stand)),
			                       bid(np.arange(stand, nstations), stand)])
			self.switching_bids = np.union1d(self.switching_bids, bids)
		self.state   = initial_state
		self.nstates = nstates
		
	def update(self, data):
		if self.state != self.STATE_SKY:
			# Zero-out all switching baselines for this frame
			data[:,self.switching_bids,...] = 0
		self.state += 1
		self.state %= self.nstates
		return super(SwitchingVisIntegrator, self).update(data)

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
	import numpy as np
	import time
	
	parser = argparse.ArgumentParser(description="LEDA post-correlation processor")
	parser.add_argument("-tp", "--totalpower", action="store_true",
	                    help="Enable total power recording")
	parser.add_argument("-corr", "--correlator", action="store_true",
	                    help="Enable correlator recording")
	parser.add_argument("-bdi", "--bdi", action="store_true",
	                    help="Enable baseline-dependent integrations for correlator (BDI)")
	#parser.add_argument("-ts", "--transients", action="store_true",
	#                    help="Enable transient search output")
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
		log.warning("No support for binding thread to core yet!")
	else:
		log.notice("Not binding thread to any particular core")
		
	log.info("Initialising input pipe")
	inpipe      = sys.stdin
	HEADER_SIZE = 4096
	
	log.info("Reading header from input pipe")
	headerstr = inpipe.read(HEADER_SIZE)
	if len(headerstr) == 0:
		log.error("EOD received before header")
		sys.exit(-1)
	if len(headerstr) < HEADER_SIZE:
		log.warning("Only read %i header bytes (expected %i)" \
			            % (len(headerstr),HEADER_SIZE))
	log.info("Parsing header")
	header = parse_header(headerstr)
	log.debug("Header: " + str(header))
	
	log.info("Creating XGPUReader")
	xgpu_reader = XGPUReader(header)
	npol = xgpu_reader.npol
	
	utc_start = header['UTC_START']
	outstem = os.path.join(args.outpath, utc_start)
	log.info("Output stem set to %s" % (outstem,))
	
	tp_integrator        = None
	corr_integrator      = None
	transient_integrator = None
	
	# TODO: Get this properly from somewhere!
	# IMPORTANT: These not only need to change, but need to be input-specific!
	#              Probably need to use tuples of (stand,pol)
	outriggers = [252,253,254,255,256]
	
	if args.totalpower:
		log.notice("Total power recording enabled")
		tpheader = header.copy()
		tpheader["DATA_ORDER"] = "time_state_bin_station_chan_pol"
		tp_writer = SimpleBinaryWriter(tpheader, outstem, suffix=".tp",
		                               max_filesize=(128*1024*1024))
		#tp_writer = SDFITSWriter( )
		tp_integrator = TotalPowerIntegrator(stands=outriggers,
		                                     #navg=3, nbuf=60)
		                                     #navg=3, nbuf=3)
		                                     navg=1, nbuf=3)
	
	# TODO: Get this working!
	if args.correlator:
		log.warning("Correlator recording not supported yet!")
		"""
		log.notice("Correlator recording enabled")
		if args.bdi:
			#corr_integrator = BDIIntegrator( )
			log.error("BDI mode not yet supported!")
		else:
			STATE_SKY = SwitchingVisIntegrator.STATE_SKY
			corr_integrator = SwitchingVisIntegrator(switching_stands=outriggers,
			                                         initial_state=STATE_SKY,
			                                         nstates=3,
			                                         navg=9,
			                                         nbuf=1)
			corr_writer = LedaFits()
		"""
	
	log.info("Entering pipeline loop")
	
	log.notice("Waiting to read from input pipe")
	rawdata = np.fromfile(inpipe, dtype=np.uint8, count=xgpu_reader.rawsize())
	while len(rawdata) == xgpu_reader.rawsize():
		log.info("Converting raw data")
		start_time = time.time()
		data = xgpu_reader.process(rawdata)
		run_time = time.time() - start_time
		log.debug("  Time = %f s" % run_time)
		log.debug("       = %f Hz" % (1./run_time,))
		
		if tp_integrator is not None:
			log.notice("Updating total power integrator")
			tp_data = tp_integrator.update(data)
			if tp_data is not None:
				log.notice("Writing total power integrations")
				tp_writer.write(tp_data)
		"""
		# TODO: Get this working!
		if corr_integrator is not None:
			corr_data = corr_integrator.update(data)
			if corr_data is not None:
				# TODO: Wrap this in a new writer object that takes care
				#         of filename management.
				corr_writer.readDada(n_ant=header['NSTATION'],
				                     n_pol=header['NPOL'],
				                     n_chans=header['NCHAN'],
				                     n_stk=header['NPOL']**2,
				                     header_dict=header,
				                     data_arr=corr_data)
				corr_writer.exportFitsidi(filename_out,
				                          verbose=False)
		"""
		log.notice("Waiting to read from input pipe")
		rawdata = np.fromfile(inpipe, dtype=np.uint8, count=xgpu_reader.rawsize)
	
	if len(rawdata) > 0:
		log.warning("Final data read was incomplete (%f%% of expected)" \
			            % (float(len(rawdata))/xgpu_reader.rawsize))
	log.notice("EOD reached")
	log.notice("All done, exiting")
