#!/usr/bin/env python

"""

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
		print "Executing:", cmdline
		logfile = open(self.logpath, 'a')
		self.process = subprocess.Popen(args, shell=True,
		                                stdout=logfile, stderr=logfile)
	def kill(self):
		# TODO: Could use self.process.terminate, but this method
		#         will interoperate with manual process execution.
		basename = os.path.basename(self.path)
		ret = subprocess.call("killall " + basename, shell=True)
		return ret
	def clearLog(self):
		if os.path.exists(self.logpath):
			os.remove(self.logpath)
	def isRunning(self):
		# TODO: Could use self.poll, but this method
		#         will interoperate with manual process execution.
		basename = os.path.basename(self.path)
		return process_running(basename)

class LEDADiskProcess(LEDAProcess):
	def __init__(self, logpath, path, bufkey, outpath, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.bufkey  = bufkey
		self.outpath = outpath
		self.core    = core
	def start(self):
		args = "-b%i -s -W -k %s -D %s" % (self.core, self.bufkey, self.outpath)
		#args = ["-b%i"%self.core, "-s", "-W",
		#        "-k", self.bufkey, "-D", self.outpath]
		self._startProc(args)

class LEDAXEngineProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey, gpu, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.gpu        = gpu
		self.core       = core
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c%i" % self.core
		args += " -g %i %s %s" % (self.gpu, self.in_bufkey, self.out_bufkey)
		#args = []
		#if self.core is not None:
		#	args += ["-c%i"%self.core]
		#args += ["-g", str(self.gpu), self.in_bufkey, self.out_bufkey]
		self._startProc(args)

class LEDAUnpackProcess(LEDAProcess):
	def __init__(self, logpath, path, in_bufkey, out_bufkey, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.logpath    = logpath
		self.path       = path
		self.in_bufkey  = in_bufkey
		self.out_bufkey = out_bufkey
		self.core       = core
	def start(self):
		args = ""
		if self.core is not None:
			args += " -c%i" % self.core
		args += " %s %s" % (self.in_bufkey, self.out_bufkey)
		#args = []
		#if self.core is not None:
		#	args += ["-c%i"%self.core]
		#args += [self.in_bufkey, self.out_bufkey]
		self._startProc(args)

class LEDACaptureProcess(LEDAProcess):
	def __init__(self, logpath, path, headerpath, bufkey, ip, port,
	             ninput, controlport=None, core=None):
		LEDAProcess.__init__(self, logpath, path)
		self.headerpath  = headerpath
		self.bufkey      = bufkey
		self.ip          = ip
		self.port        = port
		self.ninput      = ninput
		self.controlport = controlport
		self.core        = core
	def _createUTCHeaderFile(self):
		base, ext = os.path.splitext(self.headerpath)
		utcheaderpath = base + "_utc" + ext
		shutil.copyfile(self.headerpath, utcheaderpath)
		utcheaderfile = open(utcheaderpath, 'a')
		utc = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
		utcheaderfile.write("UTC_START " + utc)
		utcheaderfile.close()
		return utcheaderpath
	def start(self):
		utcheaderpath = self._createUTCHeaderFile()
		args = ""
		if self.controlport is not None:
			args += " -c %i" % self.controlport
		if self.core is not None:
			args += " -b %i" % self.core
		args += " -k %s -i %s -p %i -f %s -n%i" % \
		    (self.bufkey, self.ip, self.port, utcheaderpath, self.ninput)
		"""
		args = ["-k", self.bufkey, "-i", self.ip,
		        "-p", str(self.port), "-f", utcheaderpath,
		        "-n%i"%self.ninput]
		if self.controlport is not None:
			args += ["-c", str(self.controlport)]
		if self.core is not None:
			args += ["-b", str(self.core)]
		"""
		self._startProc(args)

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

class LEDAServer(object):
	def __init__(self, name,
	             dadapath, bufkeys, bufsizes, bufcores,
	             capture_logfiles, capture_path, capture_headerpaths,
	             capture_bufkeys, capture_ips, capture_ports,
	             capture_ninputs, capture_controlports, capture_cores,
	             unpack_logfiles, unpack_path, unpack_bufkeys,
	             xengine_logfiles, xengine_path, xengine_bufkeys,
	             xengine_gpus, xengine_cores,
	             disk_logfiles, disk_path, disk_outpaths, disk_cores,
	             debuglevel=1):
		self.name = name
		self.buffers = [LEDABuffer(dadapath,bufkey,size,core) \
			                for bufkey,size,core in \
			                zip(bufkeys,bufsizes,bufcores)]
		self.capture = [LEDACaptureProcess(logfile,capture_path,headerpath,
		                                   bufkey,ip,port,ninput,controlport,
		                                   core) \
			                for (logfile,headerpath,bufkey,ip,port,ninput,
			                     controlport,core) \
			                in zip(capture_logfiles,capture_headerpaths,
			                       capture_bufkeys,capture_ips,capture_ports,
			                       capture_ninputs,capture_controlports,
			                       capture_cores)]
		self.unpack = [LEDAUnpackProcess(logfile,unpack_path,in_bufkey,
		                                 out_bufkey,core) \
			               for logfile,in_bufkey,out_bufkey,core \
			               in zip(unpack_logfiles,capture_bufkeys,
			                      unpack_bufkeys,unpack_cores)]
		self.xengine = [LEDAXEngineProcess(logfile,xengine_path,in_bufkey,
		                                   out_bufkey,gpu,core) \
			                for logfile,in_bufkey,out_bufkey,gpu,core \
			                in zip(xengine_logfiles,unpack_bufkeys,
			                       xengine_bufkeys,xengine_gpus,xengine_cores)]
		self.disk = [LEDADiskProcess(logfile,disk_path,bufkey,outpath,core) \
			             for logfile,bufkey,outpath,core \
			             in zip(disk_logfiles,xengine_bufkeys,disk_outpaths,
			                    disk_cores)]
		
		self.debuglevel = debuglevel
		
	"""
	@property
	def nstreams(self):
		return len(self.capture)
	"""
	def getStatus(self):
		status = []
		for capture_proc,unpack_proc,xengine_proc,disk_proc in \
			    zip(self.capture,self.unpack,self.xengine,self.disk):
			capture = 'ok' if capture_proc.isRunning() else 'down'
			unpack  = 'ok' if unpack_proc.isRunning()  else 'down'
			xengine = 'ok' if xengine_proc.isRunning() else 'down'
			disk    = 'ok' if disk_proc.isRunning()    else 'down'
			disk_info = getDiskInfo(disk_proc.outpath)
			status.append({'capture':capture,
			               'unpack':unpack,
			               'xengine':xengine,
			               'disk':disk,
			               'disk_info':disk_info})
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
	def armPipeline(self):
		for disk_proc in self.disk:
			disk_proc.start()
		#time.sleep(1)
		for unpack_proc in self.unpack:
			unpack_proc.start()
		#time.sleep(1)
		for xengine_proc in self.xengine:
			xengine_proc.start()
		time.sleep(1)
	def startPipeline(self):
		for capture_proc in self.capture:
			capture_proc.start()
	def killPipeline(self):
		for capture_proc in self.capture:
			capture_proc.kill()
		for disk_proc in self.disk:
			disk_proc.kill()
		for unpack_proc in self.unpack:
			unpack_proc.kill()
		for xengine_proc in self.xengine:
			xengine_proc.kill()
		time.sleep(2)
	def clearLogs(self):
		for capture_proc in self.capture:
			capture_proc.clearLog()
		for disk_proc in self.disk:
			disk_proc.clearLog()
		for unpack_proc in self.unpack:
			unpack_proc.clearLog()
		for xengine_proc in self.xengine:
			xengine_proc.clearLog()

def onMessage(ledaserver, message, clientsocket, address):
	args = dict([x.split('=') for x in message.split('&')])
	#print "Received:", args
	
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
		ledaserver.armPipeline()
		clientsocket.send('ok')
	if 'start' in args:
		logMsg(1, DL, "Starting pipeline")
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
	
if __name__ == "__main__":
	import functools
	try:
		servername = sys.argv[1]
		
		logpath = "/home/leda/logs"
		
		ninput = 64
		nchan  = 300
		ntime  = 8192
		bufsize = ninput*nchan*ntime
		upsize  = bufsize * 2
		
		dadapath = "/home/leda/software/psrdada/src"
		bufkeys  = ["dada", "adda", "aeda", "eada",
		            "fada", "afda", "cada", "acda",
		            "abda", "aada", "bcda", "bada"]
		bufsizes = [bufsize]*8 + [upsize]*4
		bufcores = [1, 1, 9, 9,
		            9, 1, 1, 9,
		            1, 1, 9, 9]
		
		# -----------------------
		# Parameters for ledagpu4
		# -----------------------
		capture_bufkeys     = ["dada", "adda", "eada", "aeda"]
		capture_logfiles    = [os.path.join(logpath,"udpdb."+bufkey) for bufkey in capture_bufkeys]
		capture_path        = "/home/leda/software/psrdada/leda/src/leda_udpdb_thread"
		headerpath          = "/home/leda/roach_scripts/"
		capture_headerpaths = [os.path.join(headerpath,"header64%s.txt"%x) for x in ['a','b','c','d']]
		if servername == "ledagpu3":
			capture_ips         = ["192.168.0.81", "192.168.0.97", "192.168.0.113", "192.168.0.129"]
			capture_ports       = [4005, 4006, 4008, 4007]
		elif servername == "ledagpu4":
			capture_ips         = ["192.168.0.17", "192.168.0.65", "192.168.0.49", "192.168.0.33"]
			capture_ports       = [4001, 4004, 4003, 4002]
		else:
			print "Unknown server", servername
			sys.exit(-1)
		capture_ninputs     = [8] * 4
		capture_controlports = [12340,12341,12342,12343]
		capture_cores       = [1, 2, 15, 9]
		
		unpack_bufkeys      = ["aada", "abda", "bada", "bcda"]
		unpack_logfiles     = [os.path.join(logpath,"unpack."+bufkey) for bufkey in unpack_bufkeys]
		unpack_path         = "/home/leda/software/psrdada/leda/src/leda_dbupdb_paper"
		unpack_cores        = [3, 4, 10, 11]
		
		xengine_bufkeys     = ["cada", "afda", "fada", "acda"]
		xengine_logfiles    = [os.path.join(logpath,"dbgpu."+bufkey) for bufkey in xengine_bufkeys]
		xengine_path        = "/home/leda/software/leda_ipp/leda_dbgpu"
		xengine_gpus        = [0, 1, 2, 3]
		xengine_cores       = [5, 6, 12, 13]
		
		disk_logfiles       = [os.path.join(logpath,"dbdisk."+bufkey) for bufkey in xengine_bufkeys]
		disk_path           = "/home/leda/software/psrdada/src/dada_dbdisk"
		disk_outpaths       = ["/data1/one/", "/data2/two", "/data2/one/", "/data1/two"]
		disk_cores          = [7, 7, 14, 14]
		
		ledaserver = LEDAServer(servername,
		                        
		                        dadapath,
		                        bufkeys,
		                        bufsizes,
		                        bufcores,
		                        
		                        capture_logfiles,
		                        capture_path,
		                        capture_headerpaths,
		                        capture_bufkeys,
		                        capture_ips,
		                        capture_ports,
		                        capture_ninputs,
		                        capture_controlports,
		                        capture_cores,
		                        
		                        unpack_logfiles,
		                        unpack_path,
		                        unpack_bufkeys,
		                        
		                        xengine_logfiles,
		                        xengine_path,
		                        xengine_bufkeys,
		                        xengine_gpus,
		                        xengine_cores,
		                        
		                        disk_logfiles,
		                        disk_path,
		                        disk_outpaths,
		                        disk_cores)
		
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
