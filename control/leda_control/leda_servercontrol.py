#!/usr/bin/env python

"""

TODO: Re-load config file dynamically on start (or some other event)
      Load config file into its own dict and reference directly rather
        than forwarding params around everywhere!

leda_control.py
  Listens on a socket for commands
  E.g., receives "status", "start" or "stop" and runs corresponding scripts

ledagpu3
  Run schedule1.sh
  Either run leda_reset_all.py (which runs leda_reset_header.sh)
    or server_leda_nexus.py (which runs leda_reset_header_noUTC.sh)

ledagpu4
  Run schedule1.sh
  Run leda_reset_header.sh

nvidia-smi status info to grab:
GPU 0000:84:00.0
    Product Name                    : Tesla K20Xm
    Utilization
        Gpu                         : 0 %
        Memory                      : 0 %
    Temperature
        Gpu                         : 23 C
    Power Readings
        Power Draw                  : 17.84 W
    Applications Clocks
        Graphics                    : 1002 MHz
    Compute Processes               : None

ValonSynth status info to grab:
from valon_synth import *
synth = Synthesizer("/dev/ttyUSB0")
print "Freq:    ", synth.get_frequency(SYNTH_A)
print "Ref:     ", "external" if synth.get_ref_select()==1 else "internal"
print "Ref freq:", synth.get_reference()

ADC info to grab:
adc_gain        = 1  # Multiplier 1-15
adc_gain_bits   = adc_gain | (adc_gain << 4) | (adc_gain << 8) | (adc_gain << 12)
adc_gain_reg    = 0x2a

Web GUI tabs:
Control
  Start (engage?), stop, kill
  Enable/disable/configure TP, BF, BDI, CB
  Schedule manager
Monitor
  Status info on everything
    Headnode
    ROACHes
    ADCs
    Pipeline processes
    GPUs
Data
  Visualise current or historical data
"""

from SimpleSocket import SimpleSocket
import os
import sys
import shutil
import shlex
import time
import traceback
import datetime
import subprocess
import json
import glob
#from PIL import Image # Note: Must be like this when using 'pillow' fork
import StringIO, base64

#from leda_visrenderer import generate_vismatrix_plots

#import corr,numpy,struct

port = 3141

# Debug level
DL = 1

def getCurrentDadaTimeUS():
  now = datetime.datetime.today()
  now_str = now.strftime("%Y-%m-%d-%H:%M:%S.%f")
  return now_str

def logMsg(lvl, dlvl, message):
  message = message.replace("`","'")
  if (lvl <= dlvl):
    time = getCurrentDadaTimeUS()
    if (lvl == -1):
        sys.stderr.write("[" + time + "] WARN " + message + "\n")
    elif (lvl == -2):
        sys.stderr.write("[" + time + "] ERR  " + message + "\n")
    else:
        sys.stderr.write("[" + time + "] " + message + "\n")

def process_running(name):
	output = open(os.devnull, 'w')
	ret = subprocess.call("ps -C %s --no-heading" % name, shell=True,
	                      stdout=output, stderr=output)
	return ret == 0

def getDiskInfo(path):
	df = subprocess.Popen(["df", path], stdout=subprocess.PIPE)
	output = df.communicate()[0]
	device, size, used, available, percent, mountpoint = \
	    output.split("\n")[1].split()
	return {"device": device,
	        "size": size,
	        "used": used,
	        "available": available,
	        "percent": percent,
	        "mountpoint": mountpoint}

def getGPUInfo(gpu_idx):
	df = subprocess.Popen(["nvidia-smi", "-a", "-i", str(gpu_idx)],
	                      stdout=subprocess.PIPE)
	output = df.communicate()[0]
	lines = output.split("\n")
	info = {}
	# TODO: This parsing could be made more robust in case NVIDIA change
	#         the output ordering.
	#       Actually, the proper way to do this is to use NVML
	while len(lines) != 0:
		line = lines.pop(0).strip()
		if "Product Name" in line:
			info['name'] = line.split(':')[1].strip()
		elif line.strip() == "Utilization":
			line = lines.pop(0)
			# Note: We crop off the final units characters (%, C, W, MHz)
			info['gpu_util'] = float(line.split(':')[1].strip()[:-1].strip())
			line = lines.pop(0)
			info['mem_util'] = float(line.split(':')[1].strip()[:-1].strip())
		elif line.strip() == "Temperature":
			line = lines.pop(0)
			info['temp'] = float(line.split(':')[1].strip()[:-1].strip())
		elif line.strip() == "Power Readings":
			line = lines.pop(0)
			line = lines.pop(0)
			info['power'] = float(line.split(':')[1].strip()[:-1].strip())
		elif line.strip() == "Applications Clocks":
			line = lines.pop(0)
			info['gfx_clock'] = float(line.split(':')[1].strip()[:-3].strip())
			line = lines.pop(0)
			info['mem_clock'] = float(line.split(':')[1].strip()[:-3].strip())
		# TODO: This breaks when there is something running; haven't tracked down why yet
		#elif "Compute Processes" in line:
		#	info['processes'] = line.split(':')[1].strip()
	return info

class LEDAProcess(object):
	def __init__(self, logpath, path):
		self.logpath = logpath
		self.path    = path
		self.process = None
	def _startProc(self, cmdline):
		if cmdline[0] != ' ':
			cmdline = ' ' + cmdline
		cmdline = self.path + cmdline
		args = cmdline
		#args = shlex.split(cmdline)
		#args = [self.path] + args
		#print "Executing:", cmdline
		logMsg(1, DL, "Executing: %s" % cmdline)
		logfile = open(self.logpath, 'a')
		self.process = subprocess.Popen(args, shell=True,
		                                stdout=logfile, stderr=logfile)
	def kill(self):
		if self.process is not None:
			if self.process.poll() is None:
				self.process.terminate()
			#return self.process.wait()
			# TODO: This doesn't seem to be working properly!
			self.process.wait()
		#else:
		# This allows interoperation with manual process execution
		basename = os.path.basename(self.path)
		return subprocess.call("killall " + basename, shell=True)
	def clearLog(self):
		if os.path.exists(self.logpath):
			os.remove(self.logpath)
	def isRunning(self):
		if self.process is not None:
			return self.process.poll() is None
		else:
			# This allows interoperation with manual process execution
			basename = os.path.basename(self.path)
			return process_running(basename)

class LEDAPostProcess(LEDAProcess):
	def __init__(self, logpath, path, bufkey, outpath, core=None,
	             totalpower=False, correlator=False, transients_key=None,
	             bdi=False):
		LEDAProcess.__init__(self, logpath, path)
		self.bufkey  = bufkey
		self.outpath = outpath
		self.core    = core
		self.totalpower = totalpower
		self.correlator = correlator
		self.transients_key = transients_key
		self.bdi = bdi
		if not os.path.exists(outpath):
			raise ValueError("Output path '%s' does not exist" % outpath)
	def start(self):
		subargs = ""
		if self.totalpower:
			subargs += " -tp"
		if self.correlator:
			subargs += " -corr"
		#if self.transients_key is not None:
		#	subargs += " -trkey " + self.bufkey
		if self.bdi:
			subargs += " -bdi"
		if self.core is not None:
			subargs += " -core %i" % self.core
		subargs += " -vv"
		subargs += " -o %s" % self.outpath
		
		args = ""
		args += ' -a "%s"' % subargs
		# Note: This puts both the adapter and the subprocess on the same core
		if self.core is not None:
			args += " -c %i" % self.core
		args += " -vv"
		args += " %s" % self.bufkey
		self._startProc(args)

class LEDADiskProcess(LEDAProcess):
	def __init__(self, logpath, path, bufkey, outpath, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.bufkey  = bufkey
		self.outpath = outpath
		self.core    = core
		if not os.path.exists(outpath):
			raise ValueError("Output path '%s' does not exist" % outpath)
	def start(self):
		args = "-b%i -s -W -k %s -D %s" % (self.core, self.bufkey, self.outpath)
		#args = ["-b%i"%self.core, "-s", "-W",
		#        "-k", self.bufkey, "-D", self.outpath]
		self._startProc(args)
	def _getLatestFile(self, rank=0):
		# TODO: Check that the latest file contains at least one complete
		#         matrix, and otherwise open the 2nd latest.
		return sorted(glob.glob(self.outpath + "/*.dada"),
		              key=os.path.getmtime, reverse=True)[rank]
	def getVisMatrixImages(self, stem):
		"""
		# TODO: Seriously consider returning the actual data here instead
		#         of image(s). Would avoid needing PIL+matplotlib on every
		#          server, and would potentially allow client-side
		#          customisation.
		#stem = "vismatrix"
		dadafile = self._getLatestFile()
		#print "Gen'ing vismatrix image from", dadafile
		ret = subprocess.call("/home/leda/leda_control/leda_visconverter %s %s" % (dadafile,stem),
		                      shell=True)
		if ret != 0:
			#print "Failed; trying next oldest file"
			dadafile = self._getLatestFile(rank=1)
			#print "Gen'ing vismatrix image from", dadafile
			ret = subprocess.call("/home/leda/leda_control/leda_visconverter %s %s" % (dadafile,stem),
			                      shell=True)
			if ret != 0:
				print "Failed again! WTF!?"
		image_filename = generate_vismatrix_plots(stem)
		"""
		# TODO: This is a bit of a hack. It must match the
		#         code in leda_visrenderer.py
		image_filename = stem + ".png"
		return image_filename

class LEDATPProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey,
	             core=None,
	             totalpower_outpath="",
	             totalpower_edge_time_ms=1.5):
		LEDAProcess.__init__(self, logpath, path)
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.core       = core
		self.outpath    = totalpower_outpath
		self.edge_time  = totalpower_edge_time_ms
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c %i" % self.core
		# TODO: Make this togglable via the web interface
		args += " -p %s" % (self.outpath)
		
		args += " -e " + str(self.edge_time)
		args += " %s %s" \
		    % (self.in_bufkey, self.out_bufkey)
		
		self._startProc(args)

class LEDAXEngineProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey,
	             gpu, navg, core=None): #totalpower_ncycles=100,
	             #totalpower_edge_time_ms=1.5):
		LEDAProcess.__init__(self, logpath, path)
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.gpu        = gpu
		self.navg       = navg
		self.core       = core
		#self.tp_ncycles = totalpower_ncycles
		#self.tp_edge_time = totalpower_edge_time_ms
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c %i" % self.core
		## TODO: This is for the older leda_dbgpu code
		#args += " -g %i %s %s" % (self.gpu, self.in_bufkey, self.out_bufkey)
		
		# TODO: This needs to be changed to something else after all the old
		#         ncycles code is removed. Still need to be able to toggle it.
		#if self.tp_ncycles != 0:
			"""
			# TODO: Ideally this would be set to match the proper start time
			utc = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
			total_power_outfile = os.path.join(self.tp_outpath,
			                                   "total_power_" + utc + "." + self.in_bufkey)
			"""
			#args += " -p %s" % (self.tp_outpath)
		
		args += " -d " + str(self.gpu)
		args += " -t " + str(self.navg)
		#args += " -e " + str(self.tp_edge_time)
		args += " %s %s" \
		    % (self.in_bufkey, self.out_bufkey)
		
		self._startProc(args)

class LEDABeamProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey,
	             lat, lon, standfile,
	             circular=False, aperture=None,
	             gpu=None, core=None, verbosity=0):
		LEDAProcess.__init__(self, logpath, path)
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.lat        = lat
		self.lon        = lon
		self.incoherent = False
		self.standfile  = standfile
		self.circular   = circular
		self.aperture   = aperture
		self.gpu        = gpu
		self.core       = core
		self.verbosity  = verbosity
	def start(self):
		args = ""
		if self.gpu is not None:
			args += " -d %i" % self.gpu
		if self.core is not None:
			args += " -c %i" % self.core
		if self.circular:
			args += " -b"
		if self.aperture is not None:
			args += " -a %f" % self.aperture
		if self.incoherent:
			args += " -i"
		verbosity = self.verbosity
		while verbosity > 0:
			args += " -v"
			verbosity -= 1
		while verbosity < 0:
			args += " -q"
			verbosity += 1
		args += " -s %s -- %f %f %s %s" \
		    % (self.standfile,
		       self.lat, self.lon,
		       self.in_bufkey, self.out_bufkey)
		self._startProc(args)

class LEDABasebandProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey,
	             noutchan=None,
	             core=None, verbosity=0):
		LEDAProcess.__init__(self, logpath, path)
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.noutchan   = noutchan
		self.core       = core
		self.verbosity  = verbosity
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c %i" % self.core
		if self.noutchan is not None:
			args += " -f %i" % self.noutchan
		verbosity = self.verbosity
		while verbosity > 0:
			args += " -v"
			verbosity -= 1
		while verbosity < 0:
			args += " -q"
			verbosity += 1
		args += " -- %s %s" \
		    % (self.in_bufkey, self.out_bufkey)
		self._startProc(args)

class LEDAUnpackProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey,
	             core=None, ncores=1):
		LEDAProcess.__init__(self, logpath, path)
		self.logpath    = logpath
		self.path       = path
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.core       = core
		self.ncores     = ncores
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c%i" % self.core
		args += " -n%i" % self.ncores
		args += " %s %s" % (self.in_bufkey, self.out_bufkey)
		#args = []
		#if self.core is not None:
		#	args += ["-c%i"%self.core]
		#args += [self.in_bufkey, self.out_bufkey]
		self._startProc(args)

class LEDACaptureProcess(LEDAProcess):
	def __init__(self, logpath, path, header,
	             centerfreq, subband,#bandwidth,
	             bufkey, ip, port,
	             ninput, controlport=None, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.header      = header
		self.centerfreq  = centerfreq
		self.subband     = subband
		#self.bandwidth   = bandwidth
		self.bufkey      = bufkey
		self.ip          = ip
		self.port        = port
		self.ninput      = ninput
		self.controlport = controlport
		self.core        = core
		
		## HACK TESTING
		#self.start()
	def _createUTCHeaderFile(self, mode='correlator', ra=None, dec=None):
		if mode != 'beam' or ra is None or dec is None:
			ra  = "00:00:00.0"
			dec = "00:00:00.0"
		
		utc = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
		header = self.header
		header += "CFREQ           %f\n" % self.centerfreq
		header += "SUBBAND         %i\n" % self.subband
		#header += "BW              %f\n" % self.bandwidth
		header += "RA              %s\n" % ra
		header += "DEC             %s\n" % dec
		header += "UTC_START       " + utc + "\n"
		"""
		if mode == 'beam':
			header += "SOURCE          %s\n" % "TARGET"
			header += "MODE            %s\n" % "SINGLE_BEAM" # What is this?
		else:
			header += "SOURCE          %s\n" % "DRIFT"
			#header += "MODE            %s\n" % "TPS" # What is this?
			header += "MODE            %s\n" % "CORRELATOR" # What is this?
		"""
		sky_state_phase = 0 # TODO: This needs to be worked out somehow!
		header += "SKY_STATE_PHASE %i\n" % sky_state_phase
		# Note: The header file is put in the log path for convenience
		headerpath = os.path.join(os.path.dirname(self.logpath),
		                          "header." + self.bufkey)
		## HACK TESTING
		#headerpath = "header." + self.bufkey
		
		headerfile = open(headerpath, 'w')
		headerfile.write(header)
		headerfile.close()
		return headerpath
	def start(self, mode='correlator', ra=None, dec=None):
		utcheaderpath = self._createUTCHeaderFile(mode, ra, dec)
		args = ""
		if self.controlport is not None:
			args += " -c %i" % self.controlport
		if self.core is not None:
			args += " -b %i" % self.core
		args += " -k %s -i %s -p %i -f %s -n%i" % \
		    (self.bufkey, self.ip, self.port, utcheaderpath, self.ninput)
		self._startProc(args)
	def status(self):
		# Grab the latest log entry and parse
		tail = subprocess.Popen(["tail", "-n", "1", self.logpath],
		                        stdout=subprocess.PIPE)
		output = tail.communicate()[0]
		if len(output) == 0 or output[0] == '[': # Error or line contains a message
			return {"receiving":'?', "dropping":'?', "dropped":'?', "sleeps":'?'}
		cols = output.split()
		# WAR for changes in log syntax at different values
		try:
			receiving, dropping, dropped, sleeps = output.split(',')
			receiving = float(receiving.strip()[2:-6])
			dropping  = float(dropping.strip()[2:-6])
			dropped   = int(dropped.strip()[2:-4])
			sleeps    = int(sleeps.strip()[4:])
			"""
			if len(cols) == 9:
				_,receiving,_,_,dropping,_,dropped,_,sleeps = cols
				dropping = float(dropping)
			elif len(cols) == 8:
			"R=10.046 [Gb/s], D=85.7 [MB/s], D=970757 pkts, s_s=3450806"
				_,receiving,_,dropping,_,dropped,_,sleeps = cols
				dropping = float(dropping[2:])
			elif len(cols) == 7:
				receiving,_,dropping,_,dropped,_,sleeps = cols
				receiving = float(receiving[2:])
				dropping = float(dropping[2:])
			else: # Some other message (e.g., "Terminated")
				return {"receiving":'?', "dropping":'?', "dropped":'?', "sleeps":'?'}
			receiving = float(receiving)
			dropped   = int(dropped[2:])
			sleeps    = int(sleeps[4:])
			"""
			return {"receiving": receiving,
					"dropping":  dropping,
					"dropped":   dropped,
					"sleeps":    sleeps}
		except ValueError, e:
			print e
			return {"receiving":'?', "dropping":'?', "dropped":'?', "sleeps":'?'}

class LEDABuffer(object):
	def __init__(self, dadapath, bufkey, size, core=None):
		self.dadapath = dadapath
		self.bufkey   = bufkey
		self.size     = size
		self.core     = core
	def create(self):
		self.destroy()
		cmd = os.path.join(self.dadapath,"dada_db")
		if self.core is not None:
			cmd += " -c %i" % self.core
		cmd += " -b %i -k %s -l" % (self.size, self.bufkey)
		ret = subprocess.call(cmd, shell=True)
	def destroy(self):
		cmd = os.path.join(self.dadapath,"dada_db")
		cmd += " -d -k %s" % self.bufkey
		ret = subprocess.call(cmd, shell=True)
		return ret
	def exists(self):
		output = open(os.devnull, 'w')
		cmd = os.path.join(self.dadapath,"dada_dbmeminfo")
		cmd += " -k %s" % (self.bufkey)
		ret = subprocess.call(cmd, shell=True,
		                      stdout=output, stderr=output)
		return ret == 0

class LEDAServer(object):
	def __init__(self, name,
	             dadapath, bufkeys, bufsizes, bufcores,
	             capture_logfiles, capture_path, capture_header,
	             centerfreqs, subbands, #bandwidths,
	             capture_bufkeys, capture_ips, capture_ports,
	             capture_ninputs, capture_controlports, capture_cores,
	             unpack_logfiles, unpack_path, unpack_bufkeys,
	             unpack_cores, unpack_ncores,
	             tp_logfiles,
	             tp_path,
	             tp_bufkeys,
	             tp_cores,
	             tp_edge_time,
	             xengine_logfiles, xengine_path, xengine_bufkeys,
	             xengine_gpus, xengine_navg, xengine_cores,
	             disk_logfiles, disk_path, disk_outpaths, disk_cores,
	             
	             beam_logfiles, beam_path, beam_bufkeys,
	             beam_gpus, beam_cores,
	             lat, lon, standfile,
	             
	             baseband_logfiles, baseband_path, baseband_bufkeys,
	             baseband_noutchan, baseband_cores,
	             
	             debuglevel=1):
		self.name = name
		self.buffers = [LEDABuffer(dadapath,bufkey,size,core) \
			                for bufkey,size,core in \
			                zip(bufkeys,bufsizes,bufcores)]
		self.capture = [LEDACaptureProcess(logfile,capture_path,capture_header,
		                                   centerfreq, subband,#bandwidth,
		                                   bufkey,ip,port,ninput,controlport,
		                                   core) \
			                for (logfile,
			                     centerfreq,subband,#bandwidth,
			                     bufkey,ip,port,ninput,
			                     controlport,core) \
			                in zip(capture_logfiles,
			                       centerfreqs,subbands,#bandwidths,
			                       capture_bufkeys,capture_ips,capture_ports,
			                       capture_ninputs,capture_controlports,
			                       capture_cores)]
		self.unpack = [LEDAUnpackProcess(logfile,unpack_path,in_bufkey,
		                                 out_bufkey,core,unpack_ncores) \
			               for logfile,in_bufkey,out_bufkey,core \
			               in zip(unpack_logfiles,capture_bufkeys,
			                      unpack_bufkeys,unpack_cores)]
		self.tp = [LEDATPProcess(logfile, tp_path, in_bufkey, out_bufkey,
		                         core, outpath, tp_edge_time) \
			           for logfile,in_bufkey,out_bufkey,core,outpath \
			           in zip(tp_logfiles,unpack_bufkeys,tp_bufkeys,
			                  tp_cores,disk_outpaths)]
		self.xengine = [LEDAXEngineProcess(logfile,xengine_path,in_bufkey,
		                                   out_bufkey,gpu,xengine_navg,core,outpath) \
			                for logfile,in_bufkey,out_bufkey,gpu,core,outpath \
			                in zip(xengine_logfiles,tp_bufkeys,
			                       xengine_bufkeys,xengine_gpus,xengine_cores,
			                       disk_outpaths)]
		self.disk = [LEDADiskProcess(logfile,disk_path,bufkey,outpath,core) \
			             for logfile,bufkey,outpath,core \
			             in zip(disk_logfiles,xengine_bufkeys,disk_outpaths,
			                    disk_cores)]
		
		self.post = [LEDAPostProcess(logfile,post_path,bufkey,outpath,core) \
			             for logfile,bufkey,outpath,core \
			             in zip(post_logfiles,xengine_bufkeys,disk_outpaths,
			                    disk_cores)]
		
		self.beam = [LEDABeamProcess(logfile,beam_path,in_bufkey,out_bufkey,
		                             lat,lon,standfile,
		                             gpu=gpu,core=core,verbosity=2) \
			             for logfile,in_bufkey,out_bufkey,gpu,core \
			             in zip(beam_logfiles,unpack_bufkeys,beam_bufkeys,
			                    beam_gpus,beam_cores)]
		
		self.baseband = [LEDABasebandProcess(logfile,baseband_path,in_bufkey,out_bufkey,
		                                     baseband_noutchan,
		                                     core=core,verbosity=2) \
			                 for logfile,in_bufkey,out_bufkey,core \
			                 in zip(baseband_logfiles,unpack_bufkeys,baseband_bufkeys,
			                        baseband_cores)]
		
		self.debuglevel = debuglevel
		
	"""
	@property
	def nstreams(self):
		return len(self.capture)
	"""
	def getStatus(self):
		status = []
		all_buffers_exist = True
		for buf in self.buffers:
			all_buffers_exist = all_buffers_exist and buf.exists()
		for capture_proc,unpack_proc,xengine_proc,disk_proc,post_proc,beam_proc,baseband_proc in \
			    zip(self.capture,self.unpack,self.xengine,self.disk,self.post,self.beam,self.baseband):
			capture = 'ok' if capture_proc.isRunning() else 'down'
			unpack  = 'ok' if unpack_proc.isRunning()  else 'down'
			xengine = 'ok' if xengine_proc.isRunning() else 'down'
			disk    = 'ok' if disk_proc.isRunning()    else 'down'
			post    = 'ok' if post_proc.isRunning()    else 'down'
			beam    = 'ok' if beam_proc.isRunning()    else 'down'
			baseband= 'ok' if baseband_proc.isRunning()else 'down'
			buffers = 'ok' if all_buffers_exist        else 'down'
			disk_info = getDiskInfo(disk_proc.outpath)
			capture_info = capture_proc.status()
			gpu_info = getGPUInfo(xengine_proc.gpu)
			status.append({'capture':      capture,
			               'unpack':       unpack,
			               'xengine':      xengine,
			               'disk':         disk,
			               'post':         post,
			               'beam':         beam,
			               'baseband':     baseband,
			               'disk_info':    disk_info,
			               'capture_info': capture_info,
			               'buffers':      buffers,
			               'gpu_info':     gpu_info})
		return status
		#return (self.name, status)
		#return 'capture=%s&unpack=%s&xengine=%s&disk=%s' \
		#    % (capture,unpack,xengine,disk)
	def createBuffers(self):
		for buf in self.buffers:
			buf.create()
	def destroyBuffers(self):
		for buf in self.buffers:
			buf.destroy()
	def setTotalPowerRecording(self, ncycles):
		# TODO: This is probably broken
		
		#for xengine_proc in self.xengine:
		#	xengine_proc.tp_ncycles = ncycles
		for post_proc in self.post:
			post_proc.totalpower = (ncycles != 0)
	def armPipeline(self, mode='correlator'):
		self.mode = mode
		# Set which buffers to write to disk
		if mode == 'beam' or mode == 'incoherent':
			for disk_proc,beam_proc in zip(self.disk,self.beam):
				disk_proc.bufkey = beam_proc.out_bufkey
				disk_proc.start()
		elif mode == 'baseband':
			for disk_proc,baseband_proc in zip(self.disk,self.baseband):
				disk_proc.bufkey = baseband_proc.out_bufkey
				disk_proc.start()
		else:
			for disk_proc,post_proc,xengine_proc in zip(self.disk,self.post,self.xengine):
				disk_proc.bufkey = xengine_proc.out_bufkey
				disk_proc.start()
				# TESTING new leda_dbpost
				#post_proc.bufkey = xengine_proc.out_bufkey
				#post_proc.start()
		
		#for disk_proc in self.disk:
		#	disk_proc.start()
		#time.sleep(1)
		for proc in self.unpack:
			proc.start()
		for proc in self.tp:
			proc.start()
		#time.sleep(1)
		if mode == 'beam':
			for beam_proc in self.beam:
				beam_proc.incoherent = False
				beam_proc.start()
		elif mode == 'incoherent':
			for beam_proc in self.beam:
				beam_proc.incoherent = True
				beam_proc.start()
		elif mode == 'baseband':
			for proc in self.baseband:
				proc.start()
		else:
			for xengine_proc in self.xengine:
				xengine_proc.start()
		time.sleep(1)
	def startPipeline(self, ra=None, dec=None):
		for capture_proc in self.capture:
			capture_proc.start(self.mode, ra, dec)
	def killPipeline(self):
		for proclist in [self.capture,
		                 self.disk,
		                 self.unpack,
		                 self.tp,
		                 self.xengine,
		                 self.beam,
		                 self.baseband]:
			for proc in proclist:
				proc.kill()
		time.sleep(2)
	def clearLogs(self):
		for proclist in [self.capture,
		                 self.disk,
		                 self.unpack,
		                 self.tp,
		                 self.xengine,
		                 self.beam,
		                 self.baseband]:
			for proc in proclist:
				proc.clearLog()
	def getVisMatrixImages(self):
		return [disk.getVisMatrixImages("vismatrix_str%02i"%i) \
			        for i,disk in enumerate(self.disk)]
		#return self.disk[1].getVisMatrixImages()

def onMessage(ledaserver, message, clientsocket, address):
	args = dict([x.split('=') for x in message.split('&')])
	#print "Received:", args
	
	if 'exit' in args:
		logMsg(1, DL, "Exit requested")
		clientsocket.send('ok')
		return True
	if 'nstreams' in args:
		logMsg(1, DL, "nstreams request")
		nstreams = ledaserver.nstreams
		clientsocket.send("nstreams=%i"%nstreams)
	if 'status' in args:
		logMsg(1, DL, "Status request")
		status = ledaserver.getStatus()
		encoded = json.dumps(status)
		clientsocket.send(encoded)
	if 'create_buffers' in args:
		logMsg(1, DL, "(Re-)creating buffers")
		ledaserver.createBuffers()
		clientsocket.send('ok')
	if 'destroy_buffers' in args:
		logMsg(1, DL, "Destroying buffers")
		ledaserver.destroyBuffers()
		clientsocket.send('ok')
	if 'arm' in args:
		logMsg(1, DL, "Arming pipeline")
		if 'mode' in args:
			ledaserver.armPipeline(mode=args['mode'])
		else:
			ledaserver.armPipeline()
		clientsocket.send('ok')
	if 'total_power' in args:
		tp_ncycles = int(args['total_power'])
		logMsg(1, DL, "Setting total power recording ncycles to %i" % tp_ncycles)
		ledaserver.setTotalPowerRecording(tp_ncycles)
		clientsocket.send('ok')
	if 'start' in args:
		logMsg(1, DL, "Starting pipeline")
		if 'ra' in args and 'dec' in args:
			ra  = args['ra']
			dec = args['dec']
			ledaserver.startPipeline(ra, dec)
		else:
			ledaserver.startPipeline()
		clientsocket.send('ok')
	if 'kill' in args:
		logMsg(1, DL, "Killing pipeline")
		ledaserver.killPipeline()
		clientsocket.send('ok')
	if 'clear_logs' in args:
		logMsg(1, DL, "Clearing all logs")
		ledaserver.clearLogs()
		clientsocket.send('ok')
	if 'vismatrix_images' in args:
		logMsg(1, DL, "Generating and sending visibility matrix images")
		
		imagefiles = ledaserver.getVisMatrixImages()
		encoded_images = []
		for imagefile in imagefiles:
			if not os.path.exists(imagefile):
				logMsg(1, DL, "Error: VisMatrix image %s not found" % imagefile)
				continue
			image = Image.open(imagefile)
			data = StringIO.StringIO()
			image.save(data, format="png")
			data = data.getvalue()
			encoded_image = base64.standard_b64encode(data)
			encoded_images.append(encoded_image)
		encoded = json.dumps(encoded_images)
		clientsocket.send(encoded)
		"""
		imagefile = ledaserver.getVisMatrixImages()
		image = Image.open(imagefile)
		data = StringIO.StringIO()
		image.save(data, format="png")
		data = data.getvalue()
		encoded_image = base64.standard_b64encode(data)
		encoded = json.dumps(encoded_image)
		clientsocket.send(encoded)
		"""

if __name__ == "__main__":
	import functools
	from configtools import *
	try:
		#configfile = getenv_warn('LEDA_CONFIG', "config_leda64nm.py")
		configfile = getenv('LEDA_CONFIG')
		# Dynamically execute config script
		execfile(configfile, globals())
		
		# TODO: Check for psrdada complaining about some of these
		capture_header = ""
		#capture_header += "BW              %f\n" % (-corr_bandwidth)
		#capture_header += "CFREQ           %f\n" % corr_centerfreq
		capture_header += "FREQ            %f\n" % corr_clockfreq
		capture_header += "NFFT            %i\n" % corr_nfft
		#capture_header += "RA              %s\n" % "00:00:00.0"
		#capture_header += "DEC             %s\n" % "00:00:00.0"
		
		capture_header += "HDR_SIZE        %i\n" % corr_headersize
		capture_header += "HDR_VERSION     %s\n" % corr_headerversion
		capture_header += "PID             %s\n" % "P999"
		capture_header += "TELESCOPE       %s\n" % corr_telescope
		capture_header += "RECEIVER        %s\n" % corr_receiver
		capture_header += "INSTRUMENT      %s\n" % corr_instrument
		capture_header += "SOURCE          %s\n" % "DRIFT"
		capture_header += "MODE            %s\n" % "TPS" # What is this?
		
		# Note: NBIT is re-written by the X-engine process
		capture_header += "NBIT            %i\n" % corr_nbit_in
		capture_header += "NCHAN           %i\n" % nchan
		capture_header += "NDIM            %i\n" % ndim
		capture_header += "NPOL            %i\n" % npol
		#capture_header += "NSTAND          %i\n" % (ninput/npol)
		capture_header += "NSTATION        %i\n" % (ninput/npol)
		capture_header += "OBS_OFFSET      %i\n" % 0
		capture_header += "LOWFREQ         %f\n" % lowfreq
		df = corr_clockfreq / float(corr_nfft)
		capture_header += "CHAN_WIDTH      %f\n" % df
		capture_header += "BW              %f\n" % (nchan * df)
		capture_header += "TSAMP           %f\n" % (1./df)
		capture_header += "XENGINE_NTIME   %i\n" % ntime
		capture_header += "NAVG            %i\n" % (ntime*xengine_navg)
		capture_header += "BYTES_PER_AVG   %i\n" % outsize
		
		capture_header += "COMPUTE_NODE    %s\n" % servername
		capture_header += "ROACH_BOF       %s\n" % boffile
		capture_header += "DATA_ORDER      %s\n" % corr_data_order
		
		capture_header += "ADC_GAIN        %f\n" % adc_gain
		# TODO: Work out how to get these
		capture_header += "ARX_FILTER      %s\n" % "SPLIT_BAND"
		capture_header += "ARX_GAIN        %f\n" % 1
		
		capture_header += "PROC_FILE       %s\n" % "leda.dbdisk" # What is this?
		capture_header += "OBS_XFER        %i\n" % 0 # What is this?
		# Note: Apparently BYTES_PER_SECOND is actually interpreted by psrdada
		#         as simply 1/10th the amount of data to put in the file.
		max_filesize = 2*1024**3
		bytes_per_second = (max_filesize-corr_headersize) // (outsize * 10) * outsize
		capture_header += "BYTES_PER_SECOND %i\n" % bytes_per_second
		
		centerfreqs = [lowfreq + (sb+0.5)*nchan*df for sb in subbands]
		
		ledaserver = LEDAServer(servername,
		                        
		                        dadapath,
		                        bufkeys,
		                        bufsizes,
		                        bufcores,
		                        
		                        capture_logfiles,
		                        capture_path,
		                        capture_header,
		                        centerfreqs,
		                        subbands,
		                        #bandwidths,
		                        capture_bufkeys,
		                        capture_ips,
		                        capture_ports,
		                        capture_ninputs,
		                        capture_controlports,
		                        capture_cores,
		                        
		                        unpack_logfiles,
		                        unpack_path,
		                        unpack_bufkeys,
		                        unpack_cores,
		                        unpack_ncores,
		                        
		                        tp_logfiles,
		                        tp_path,
		                        tp_bufkeys,
		                        tp_cores,
		                        tp_edge_time,
		                        
		                        xengine_logfiles,
		                        xengine_path,
		                        xengine_bufkeys,
		                        xengine_gpus,
		                        xengine_navg,
		                        xengine_cores,
		                        
		                        disk_logfiles,
		                        disk_path,
		                        disk_outpaths,
		                        disk_cores,
		                        
		                        beam_logfiles,
		                        beam_path,
		                        beam_bufkeys,
		                        beam_gpus,
		                        beam_cores,
		                        site_lat,
		                        site_lon,
		                        site_stands_file,
		                        
		                        baseband_logfiles,
		                        baseband_path,
		                        baseband_bufkeys,
		                        baseband_noutchan,
		                        baseband_cores)
		
		# TESTING
		#port = int(sys.argv[1])
		
		print "Listening for client requests on port %i..." % port
		sock = SimpleSocket()
		sock.listen(functools.partial(onMessage, ledaserver), port)
		
	except:
		logMsg(-2, DL, "main: exception caught: " + str(sys.exc_info()[0]))
		print '-'*60
		traceback.print_exc(file=sys.stdout)
		print '-'*60
