
import socket
import errno
import time

class SimpleSocket(object):
	timeout_error = socket.timeout
	generic_error = socket.error
	def __init__(self, sock=None, CHUNK_SIZE=256, timeout=None):
		if sock is None:
			self.sock = socket.socket(socket.AF_INET,
			                          socket.SOCK_STREAM)
			self.sock.setsockopt(socket.SOL_SOCKET,
			                     socket.SO_REUSEADDR, 1)
			self.sock.settimeout(timeout)
		else:
			self.sock = sock
			self.sock.setsockopt(socket.SOL_SOCKET,
			                     socket.SO_REUSEADDR, 1)
		#self.MSGLEN = MSGLEN
		self.CHUNK_SIZE = CHUNK_SIZE
		self.terminator = ';;;'
		
	def __del__(self):
		try:
			self.sock.shutdown(socket.SHUT_RDWR) # Throws when not connected
		except: #socket.error, e:
			pass
		self.sock.close()
		
	def listen(self, callback, port, host='', maxconnections=5):
		self.sock.bind((host, port))
		self.sock.listen(maxconnections)
		while True:
			# This blocks until a connection request comes in
			clientsocket, address = self.sock.accept()
			print "Connection opened to", address
			clientsocket = SimpleSocket(clientsocket)
			while True:
				try:
					msg = clientsocket.receive()
				except:
					print "Connection closed to ", address
					break
				#callback(self.sock, SimpleSocket(clientsocket), address)
				ret = callback(msg, clientsocket, address)
				# On true return value, exit
				if ret:
					return
		
	def connect(self, host, port, attempts=5):
		while attempts > 0:
			try:
				self.sock.connect((host, port))
			except socket.error, e:
				if e.errno == errno.ECONNREFUSED:
					print "Connection attempt refused"
					attempts -= 1
					time.sleep(1)
				else:
					raise
			else:
				return True
		raise timeout_error
	
	def send(self, msg):
		msg += self.terminator
		totalsent = 0
		while totalsent < len(msg):#self.MSGLEN:
			sent = self.sock.send(msg[totalsent:])
			if sent == 0:
				raise RuntimeError("socket connection broken")
			totalsent = totalsent + sent
	def send_data(self, data):
		msg = base64.standard_b64encode(data)
		self.send(msg)
	
	def receive(self, timeout="default"):
		if timeout != "default":
			old_timeout = self.sock.gettimeout()
			self.sock.settimeout(timeout)
		msg = ''
		#while len(msg) < self.MSGLEN:
		while self.terminator not in msg:
			#chunk = self.sock.recv(self.MSGLEN-len(msg))
			chunk = self.sock.recv(self.CHUNK_SIZE)
			if chunk == '':
				raise RuntimeError("socket connection broken")
			msg = msg + chunk
		if timeout != "default":
			self.sock.settimeout(old_timeout)
		return msg[:msg.find(';')]

if __name__ == "__main__":
	
	def handle_connection(msg, clientsocket, address):
		print "Accepted connection from", address
		print "Received", msg
		clientsocket.send('Thanks!')
		print "Thanks sent"
	
	port = 3141
	
	s = SimpleSocket()
	s.listen(handle_connection, 'localhost', port)
	
