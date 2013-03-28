#!/usr/bin/env python

import sys
import SimpleSocket
from SimpleSocket import SimpleSocket

port = 3141

if __name__ == "__main__":
	host = sys.argv[1]
	msg  = sys.argv[2]
	
	sock = SimpleSocket(timeout=3)
	try:
		sock.connect(host, port)
	except SimpleSocket.timeout_error:
		print "All connection attempts were refused"
		sys.exit(-1)
	
	for i in range(1):
		sock.send(msg)
		try:
			ret = sock.receive()
		except SimpleSocket.timeout_error:
			print "No response!"
		else:
			print "Response:", ret
