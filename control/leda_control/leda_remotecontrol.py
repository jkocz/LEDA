#!/usr/bin/env python

from SimpleSocket import SimpleSocket
import sys
import datetime
import json
import base64
from PIL import Image

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

class LEDARemoteHeadNodeControl(object):
	def __init__(self, host, port, log=LEDALogger()):
		self.host = host
		self.port = port
		self.log  = log
		self.connect()
	def connect(self):
		self.log.write("Connecting to remote headnode %s:%i" \
			               % (self.host,self.port))
		# TODO: See comment in leda_headnodecontrol.py
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
		else:
			if len(ret) <= 256:
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
	def getStatus(self):
		self.log.write("Requesting status", 2)
		#if self.sock is None:
		#	self.log.write("Not connected", -2)
		#	return None
		encoded = self._sendmsg("status=1")
		if encoded is None:
			return None
		#print "json.loads('%s')" % encoded
		status = json.loads(encoded)
		return status
	def getADCImages(self):
		self.log.write("Requesting ADC images", 2)
		encoded = self._sendmsg("adc_images=1")
		if encoded is None:
			return None
		#print "json.loads('%s')" % encoded
		encoded_images = json.loads(encoded)
		#images = [Image.open(base64.standard_b64decode(im))
		# TODO: This isn't great. We return the raw binary data as a string.
		images = [[base64.standard_b64decode(adc_im) for adc_im in roach] \
			          for roach in encoded_images]
		#images = [base64.standard_b64decode(im)
		#	          for im in encoded_images]
		return images
	def configure(self):
		self.log.write("Configuring", 2)
		self._sendcmd("configure=1")
	def programRoaches(self):
		self.log.write("Programming roaches", 2)
		self._sendcmd("program_roaches=1")
	def createBuffers(self):
		self.log.write("Creating buffers", 2)
		self._sendcmd("create_buffers=1")
	def startObservation(self):
		self.log.write("Starting observation", 2)
		self._sendcmd("start=1")
	def stopObservation(self):
		self.log.write("Stopping observation", 2)
		self._sendcmd("stop=1")
	def killObservation(self):
		self.log.write("Killing observation", 2)
		self._sendcmd("kill=1")
	def clearLogs(self):
		self.log.write("Clearing all logs", 2)
		self._sendcmd("clear_logs=1")
	def getVisMatrixImages(self):
		self.log.write("Requesting visibility matrix images", 2)
		encoded = self._sendmsg("vismatrix_images=1")
		if encoded is None:
			return None
		encoded_images = json.loads(encoded)
		# TODO: This isn't great. We return the raw binary data as a string.
		images = [base64.standard_b64decode(encoded_image) \
			          for encoded_image in encoded_images]
		return images

if __name__ == "__main__":
	if len(sys.argv) <= 1:
		print "Usage:", sys.argv[0], "[status|configure|start|stop|kill|program_roaches|create_buffers]"
		sys.exit(0)
	cmd = sys.argv[1]
	
	port       = 6282
	host       = "ledagpu4"
	logstream  = sys.stderr
	debuglevel = 1
	
	leda = LEDARemoteHeadNodeControl(host, port,
	                                 LEDALogger(logstream, debuglevel))
	
	if cmd == "status":
		# TODO: Consider separating servers etc. into separate LEDARemote* classes
		# TODO: Add roach status printing
		status = leda.getStatus()
		if status is not None:
			for i, ((control_host,control), (capture_host,capture)) \
				    in enumerate(zip(status["control"],
				                     status["capture"])):
				print "========="
				#print "Server %i" % i
				print "Server %s" % control_host
				print "========="
				for j, stream in enumerate(control):
					print "--------"
					print "Stream %i" % j
					print "--------"
					for key,val in stream.items():
						print "%s: %s" % (key,val)
				for j, process in enumerate(capture):
					print "-----------------"
					print "Capture process %i" % j
					print "-----------------"
					if process is None:
						print "Not connected"
					else:
						for key,val in process.items():
							print "%s: %s" % (key,val)
			for i, roach in enumerate(status["roach"]):
				print "======="
				print "Roach %i" %i
				print "======="
				for key,val in roach.items():
					print "%s: %s" % (key,val)
	elif cmd == "adc_images":
		print "Received image data"
		# TODO: Do something with it
		pass
	elif cmd == "configure":
		leda.configure()
	elif cmd == "program_roaches":
		leda.programRoaches()
	elif cmd == "create_buffers":
		leda.createBuffers()
	elif cmd == "start":
		leda.startObservation()
	elif cmd == "stop":
		leda.stopObservation()
	elif cmd == "kill":
		leda.killObservation()
	elif cmd == "clearlogs":
		leda.clearLogs()
	else:
		print "Unknown command", cmd
