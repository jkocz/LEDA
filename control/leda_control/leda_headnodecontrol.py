#!/usr/bin/env python

"""

By Ben Barsdell (2013)

TODO: Work out how to provide intermediate state information like "Starting..."
      Add management of output data
      Look into getting data plots
      Write webserver interface (connect to this app with another socket)

adc16_plot_chans.rb --length=1024 --chans=C4 -s 169.254.128.14
plot adc channel C4 on roach .14 with 1024 points
adc16_plot_chans.rb --length=1024 -s 169.254.128.14
plot all channels with 1024 points

"""

from leda_dada_utils import *
from leda_program_roach import programRoach
from SimpleSocket import SimpleSocket
import corr
import sys
import json
import time, datetime
import subprocess
import shutil
#from PIL import Image # Note: Must be like this when using 'pillow' fork
import StringIO, base64
from leda_logger import LEDALogger
"""
class LEDALogger(object):
	def __init__(self, streams=sys.stderr, debuglevel=1):
		try:
			streams.write("")
		except:
			self.streams = streams
		else:
			self.streams = [streams]
		self.debuglevel = debuglevel
	def copy(self):
		return LEDALogger(self.streams, self.debuglevel)
	def curTime(self):
		now = datetime.datetime.today()
		now_str = now.strftime("%Y-%m-%d-%H:%M:%S.%f")
		return now_str
	def write(self, message, level=1):
		output = "[" + self.curTime() + "]"
		if level == -1:
			output += " WARN"
		elif level == -2:
			output += " ERR"
		output += " " + message.replace("`","'") + "\n"
		for stream in self.streams:
			stream.write(output)
"""
class LEDARemoteServerControl(object):
	def __init__(self, host, port, log=LEDALogger()):
		self.host = host
		self.port = port
		self.log  = log
		self.connect()
	def connect(self):
		self.log.write("Connecting to remote server %s:%i" \
			               % (self.host,self.port))
		#self._nstreams = None
		# TODO: This timeout must be long enough to cover long
		#         operations on the server. This is not a good
		#         way to do things; would probably be better to
		#         send an instant response and something like
		#         an asynchronous "I'll get back to you in N secs".
		self.sock = SimpleSocket(timeout=10)
		try:
			self.sock.connect(self.host, self.port)
		except SimpleSocket.timeout_error:
			self.log.write("All connections were refused", -2)
			self.sock = None
		except:
			self.log.write("Failed to connect. "+str(sys.exc_info()[1]), -2)
			self.sock = None
		else:
			self.log.write("Connection successful")
	def isConnected(self):
		return self.sock is not None
	def _sendmsg(self, msg):
		if self.sock is None:
			self.log.write("Not connected", -2)
			return None
		if len(msg) <= 256:
			self.log.write("Sending message "+msg, 4)
		else:
			self.log.write("Sending long message of length %i bytes"%(len(msg)), 4)
		try:
			self.sock.send(msg)
			ret = self.sock.receive()
		except:
			self.log.write("Not connected", -2)
			self.sock = None
			return None
		if len(ret) < 256:
			self.log.write("Received response "+ret, 4)
		else:
			self.log.write("Received long response of length %i bytes"%(len(ret)), 4)
		return ret
	def _sendcmd(self, cmd):
		ret = self._sendmsg(cmd)
		if ret is None:
			return
		if ret != 'ok':
			self.log.write("Remote command failed", -2)
			raise Exception("Remote command failed")
	"""
	@property
	def nstreams(self):
		if self._nstreams is not None:
			return self._nstreams
		self.log.write("Requesting value of nstreams", 3)
		if self.sock is None:
			self.log.write("Not connected", -2)
			return None
		ret = self._sendmsg("nstreams=1")
		if ret is None:
			return None
		if "nstreams" in ret:
			self._nstreams = int(ret.split('=')[1])
			return self._nstreams
		else:
			return None
	"""
	def getStatus(self):
		self.log.write("Requesting server status", 2)
		if self.sock is None:
			self.log.write("Not connected", -2)
			return None
		encoded = self._sendmsg("status=1")
		if encoded is None:
			return None
		status = json.loads(encoded)
		return status
		"""
		stream_stats = []
		for stream in self.nstreams:
			ret = self._sendmsg("status=1&stream=%i"%stream)
			args = dict([x.split('=') for x in ret.split('&')])
			stream_stats.append(args)
		return stream_stats
		"""
	def createBuffers(self):
		self.log.write("Creating buffers", 2)
		self._sendcmd("create_buffers=1")
	def destroyBuffers(self):
		self.log.write("Destroying buffers", 2)
		self._sendcmd("destroy_buffers=1")
	def setTotalPowerRecording(self, ncycles):
		self.log.write("Setting total power recording param", 2)
		self._sendcmd("total_power=%i" % ncycles)
	def armPipeline(self):
		self.log.write("Arming pipeline", 2)
		self._sendcmd("arm=1")
	def startPipeline(self):
		self.log.write("Starting pipeline", 2)
		self._sendcmd("start=1")
	def killPipeline(self):
		self.log.write("Killing pipeline", 2)
		self._sendcmd("kill=1")
	def clearLogs(self):
		#self.log.write("Clearing all logs", 2)
		self._sendcmd("clear_logs=1")
	def getVisMatrixImages(self):
		self.log.write("Requesting visibility matrix images", 2)
		encoded = self._sendmsg("vismatrix_images=1")
		if encoded is None:
			return None
		encoded_images = json.loads(encoded)
		return encoded_images
	def exit(self):
		self.log.write("Requesting server control script to exit", 2)
		self._sendcmd("exit=1")

class LEDARemoteCaptureProcess(object):
	def __init__(self, host, port, log=LEDALogger()):
		self.host = host
		self.port = port
		self.log = log
		self.sock = None
		# TODO: Probably better to call this manually later
		#self.connect()
	def connect(self):
		self.log.write("Connecting to remote process at %s:%i" \
			               % (self.host,self.port))
		#try:
		self.sock = openSocket(self.log.debuglevel,
		                       self.host, self.port, attempts=2)#3)
		#except:
		if self.sock is None:
			self.log.write("Failed to connect. "+str(sys.exc_info()[1]), -2)
			self.sock = None
		else:
			self.log.write("Connection successful")
	def isConnected(self):
		return self.sock is not None
	def _sendmsg(self, msg):
		result, response = sendTelnetCommand(self.sock, msg)
		if result != 'ok':
			self.log.write("Command '%s' failed" % msg, -2)
			return None
		return response
	def start(self, utcstr=None):
		if utcstr is not None:
			self._sendmsg("SET_UTC_START "+utcstr)
		self.log.write("Scheduling capture start")
		self._sendmsg("START")
	def getStatus(self):
		if self.sock is None:
			#self.log.write("Not connected", -2)
			return None
		self.log.write("Requesting capture process status", 2)
		sock = self.sock
		# Note: result is either 'ok' or 'fail'
		result, response = sendTelnetCommand(sock, "STATS")
		if result != 'ok':
			self.log.write("Command failed")
			return None
			#raise Exception('capture::get_status failed')
		if '=' not in response:
			self.log.write("Unexpected response: "+response)
			return None
		args = dict([x.split('=') for x in response.split(',')])
		mb_total = float(args['mb_total'])
		if mb_total == 0:
			buf_use = 0
		else:
			buf_use = float(args['mb_free']) / mb_total
		return {"received":   float(args['mb_rcv_ps']),
				"dropped":    float(args['mb_drp_ps']),
				"packets":    int(args['ooo_pkts']),
				"buffer_use": buf_use}

class LEDARemoteCapture(object):
	def __init__(self, host, ports, log=LEDALogger()):
		self.processes = [LEDARemoteCaptureProcess(host, port, log) \
			                  for port in ports]

class LEDARemoteServer(object):
	def __init__(self, host, controlport, captureports, log=LEDALogger()):
		self.host = host
		self.control = LEDARemoteServerControl(host, controlport, log)
		self.capture = LEDARemoteCapture(host, captureports, log)

class LEDARoach(object):
	def __init__(self, host, port,
	             boffile, fids, src_ips, src_ports, dest_ips, dest_ports,
	             first_chan, last_chan, nchan, gain_coef,
	             have_adcs=True, use_progdev=False,
	             registers={}, fft_shift_mask=0xFFFF,
	             log=LEDALogger()):
		self.host = host
		self.port = port
		self.boffile     = boffile
		self.fids        = fids
		self.src_ips     = src_ips
		self.src_ports   = src_ports
		self.dest_ips    = dest_ips
		self.dest_ports  = dest_ports
		self.first_chan  = first_chan
		self.last_chan   = last_chan
		self.nchan       = nchan
		self.gain_coef   = gain_coef
		self.have_adcs   = have_adcs
		self.use_progdev = use_progdev
		self.registers   = registers
		self.fft_shift_mask = fft_shift_mask
		self.reset_cmd = 'adc_rst' if have_adcs else 'fft_rst'
		self.log  = log
		self.connect()
	def connect(self):
		self.log.write("Connecting to ROACH %s:%i" % (self.host,self.port))
		self.fpga = corr.katcp_wrapper.FpgaClient(self.host, self.port)
		time.sleep(0.5)
		if not self.fpga.is_connected():
			self.log.write("Failed to connect", -2)
			self.fpga = None
	def isConnected(self):
		return self.fpga is not None
	def armFlow(self):
		self.log.write("Arming ROACH flow")
		#if self.fpga == None:
		if not self.fpga.is_connected():
			self.log.write("Not connected", -2)
			return
		self.fpga.write_int(self.reset_cmd,3)
		self.fpga.write_int('tenge_enable',1)
	def startFlow(self):
		self.log.write("Starting ROACH flow")
		#if self.fpga == None:
		if not self.fpga.is_connected():
			self.log.write("Not connected", -2)
			return
		self.fpga.write_int(self.reset_cmd,0)
	def stopFlow(self):
		self.log.write("Stopping ROACH flow")
		if self.fpga == None:
			self.log.write("Not connected", -2)
			return
		self.fpga.write_int('tenge_enable',0)
	def isFlowing(self):
		if self.fpga == None:
			self.log.write("Not connected", -2)
			return None
		try:
			tenge_enable = self.fpga.read_int('tenge_enable')
			adc_rst      = self.fpga.read_int(self.reset_cmd)
		except RuntimeError:
			self.log.write("[%s] Read request 'tenge_enable' or 'fft_rst' failed" % self.host, -2)
			return None
		return tenge_enable and adc_rst == 0
	def getStatus(self):
		flow = self.isFlowing()
		return {'flow': 'error' if flow is None else 'ok' if flow else 'down'}
	def getADCImages(self):
		self.log.write("Generating ADC input plots")
		# TODO: This code is very specific to the current (LEDA64) setup
		outfilename = "adc_plots_%s" % self.host
		ret = subprocess.call("adc16_plot_chans.rb --length=1024 --stats -d %s/png %s" \
			                      % (outfilename, self.host),
		                      shell=True)
		if ret != 0:
			print "Call to adc16_plot_chans.rb FAILED"
		#shutil.move(outfilename,      outfilename+"_1.png")
		#shutil.move(outfilename+"_2", outfilename+"_2.png")
		shutil.copy(outfilename,      outfilename+"_1.png")
		shutil.copy(outfilename+"_2", outfilename+"_2.png")
		return (outfilename+"_1.png", outfilename+"_2.png")
		
	def program(self):
		self.log.write("Programming ROACH")
		if self.fpga == None:
			self.log.write("Not connected", -2)
			return
		programRoach(self.fpga, self.boffile, self.fids,
		             self.src_ips, self.src_ports,
		             self.dest_ips, self.dest_ports,
		             self.first_chan, self.last_chan, self.nchan,
		             self.gain_coef, self.have_adcs, self.use_progdev,
		             self.registers, self.fft_shift_mask)

class LEDARemoteManager(object):
	def __init__(self, serverhosts, roachhosts,
	             controlport, captureports, roachport,
	             boffile, all_fids, all_src_ips, src_ports, dest_ips, dest_ports,
	             first_chan, last_chan, nchan, gain_coef,
	             have_adcs, use_progdev, registers, fft_shift_mask,
	             log=LEDALogger()):
		self.log = log
		self.servers = [LEDARemoteServer(host,controlport,
		                                 captureports,log) \
			                for i,host in enumerate(serverhosts)]
		self.roaches = [LEDARoach(host,roachport,
		                          boffile,fids,src_ips,src_ports,
		                          dest_ips,dest_ports,
		                          first_chan,last_chan,nchan,gain_coef,
		                          have_adcs,use_progdev,
		                          registers,fft_shift_mask,
		                          log) \
			                for host,fids,src_ips \
			                in zip(roachhosts,all_fids,all_src_ips)]
	
	def programRoaches(self):
		self.log.write("Programming roaches; wait 3 mins to take effect", 0)
		for roach in self.roaches:
			roach.program()
		# Note: Very important, wait for ARP tables in ROACHes to update
		#time.sleep(180)
	def createBuffers(self):
		self.log.write("Creating buffers", 0)
		for server in self.servers:
			server.control.createBuffers()
	def setTotalPowerRecording(self, ncycles):
		self.log.write("Setting total power recording param", 0)
		for server in self.servers:
			server.control.setTotalPowerRecording(ncycles)
	def exit(self):
		for server in self.servers:
			server.control.exit()
	def configure(self):
		self.log.write("Configuring hardware", 0)
		self.programRoaches()
		self.createBuffers()
		"""
		for roach in self.roaches:
			roach.program()
		for server in self.servers:
			server.control.createBuffers()
		# Note: Very important, wait for ARP tables in ROACHes to update
		time.sleep(180)
		"""
	def startObservation(self):
		self.log.write("Starting observation", 0)
		self.killObservation()
		self.clearLogs()
		## TODO: Replace this procedure with synchronised start method
		
		start_delay = 10 # seconds
		roach_start_delay = 2
		
		for server in self.servers:
			server.control.armPipeline()
		for roach in self.roaches:
			roach.armFlow()
		for server in self.servers:
			server.control.startPipeline()
			for process in server.capture.processes:
				process.connect()
		#time.sleep(10)
		#for roach in self.roaches:
		#	roach.startFlow()
		
		# |0| | | | | | | |r| |*|
		
		# Perform synchronised start
		wait_for_1sec_boundary()
		time.sleep(0.5)
		utc   = datetime.datetime.utcnow()
		delta = datetime.timedelta(0, start_delay)
		utc  += delta
		utcstr = utc.strftime("%Y-%m-%d-%H:%M:%S")
		delta = datetime.timedelta(0, roach_start_delay)
		roach_start_time = (utc - delta).strftime("%Y-%m-%d-%H:%M:%S")
		
		self.log.write("Scheduling capture procs to start at "+utcstr)
		for server in self.servers:
			for process in server.capture.processes:
				process.start(utcstr)
		self.log.write("Waiting for start time")
		wait_until_utc_sec(roach_start_time)
		time.sleep(0.5)
		self.log.write("Starting flow from ROACHes")
		for roach in self.roaches:
			roach.startFlow()
		
	def stopObservation(self):
		self.log.write("Stopping observation", 0)
		for roach in self.roaches:
			roach.stopFlow()
	def killObservation(self):
		self.log.write("Killing observation", 0)
		self.stopObservation()
		for server in self.servers:
			server.control.killPipeline()
	def clearLogs(self):
		self.log.write("Clearing all logs", 0)
		for server in self.servers:
			server.control.clearLogs()

def onMessage(leda, message, clientsocket, address):
	args = dict([x.split('=') for x in message.split('&')])
	
	if "status" in args:
		control_status = [(server.host,server.control.getStatus()) for server in leda.servers]
		"""
		capture_status = [[(server.host,process.getStatus()) \
			                   for process in server.capture.processes] \
			                  for server in leda.servers]
        """
		roach_status = [roach.getStatus() for roach in leda.roaches]
		#roach_status = [{"flowing": str(roach.isFlowing())} for roach in leda.roaches]
		status = {"control": control_status,
		          #"capture": capture_status,
		          "roach":   roach_status}
		encoded = json.dumps(status)
		clientsocket.send(encoded)
	elif "adc_images" in args:
		roach_adc_imagenames = [roach.getADCImages() for roach in leda.roaches]
		encoded_images = []
		for roach in roach_adc_imagenames:
			encoded_images.append([])
			for adc_imagename in roach:
				#print "**** Wrote ADC plots to", adc_imagename
				image = Image.open(adc_imagename)
				data = StringIO.StringIO()
				image.save(data, format="png")
				data = data.getvalue()
				encoded_image = base64.standard_b64encode(data)
				encoded_images[-1].append(encoded_image)
		encoded = json.dumps(encoded_images)
		#print encoded
		print "Sending ADC plot image data"
		clientsocket.send(encoded)
	if "exit" in args:
		leda.exit()
		clientsocket.send('ok')
	elif "configure" in args:
		leda.configure()
		clientsocket.send('ok')
	elif "program_roaches" in args:
		leda.programRoaches()
		clientsocket.send('ok')
	elif "create_buffers" in args:
		leda.createBuffers()
		clientsocket.send('ok')
	elif "total_power" in args:
		tp_ncycles = int(args["total_power"])
		leda.setTotalPowerRecording(tp_ncycles)
		clientsocket.send('ok')
	elif "start" in args:
		leda.startObservation()
		clientsocket.send('ok')
	elif "stop" in args:
		leda.stopObservation()
		clientsocket.send('ok')
	elif "kill" in args:
		leda.killObservation()
		clientsocket.send('ok')
	elif "clear_logs" in args:
		leda.clearLogs()
		clientsocket.send('ok')
	elif "vismatrix_images" in args:
		# TODO: Currently only requesting image from ledagpu4
		encoded_images = leda.servers[1].control.getVisMatrixImages()
		encoded = json.dumps(encoded_images)
		print "Sending visibility matrix image data"
		clientsocket.send(encoded)
	else:
		clientsocket.send('error: unknown command')
		print "Unknown command", args

if __name__ == "__main__":
	from configtools import *
	import functools
	#from SimpleSocket import SimpleSocket
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	execfile(configfile, globals())
	
	controlport  = 3141
	logstream    = sys.stderr
	debuglevel   = 1
	
	leda = LEDARemoteManager(serverhosts, roachhosts,
	                         controlport, capture_controlports, roachport,
	                         boffile, fids,
	                         src_ips, src_ports,
	                         dest_ips, dest_ports,
	                         fft_first_chan, fft_last_chan, nchan, fft_gain_coef,
	                         have_adcs, use_progdev,
	                         roach_registers, fft_shift_mask,
	                         LEDALogger(logstream, debuglevel))
	
	port = 6282
	
	print "Listening for client requests on port %i..." % port
	sock = SimpleSocket()
	sock.listen(functools.partial(onMessage, leda), port)
