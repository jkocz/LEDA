
import sys
from SimpleSocket import SimpleSocket

class LEDAClient(object):
	def __init__(self, host, port, log):
		self.host = host
		self.port = port
		self.log  = log
		self.connect()
	def connect(self):
		self.log.write("Connecting to remote server %s:%i" \
			               % (self.host,self.port))
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
			return None
		if ret == 'ok':
			return True
		else:
			self.log.write("Remote command failed", -2)
			raise Exception("Remote command failed")
