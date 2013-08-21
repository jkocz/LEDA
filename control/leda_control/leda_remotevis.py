#!/usr/bin/env python

import sys
import datetime
import json
import base64
from leda_client import LEDAClient
from leda_logger import LEDALogger

def receive_image(encoded_image):
	if encoded_image is None:
		return None
	imgdata = base64.standard_b64decode(encoded_image)
	return imgdata

class LEDARemoteHeadNodeVis(LEDAClient):
	def __init__(self, host, port, log=LEDALogger()):
		super(LEDARemoteHeadNodeVis, self).__init__(host, port, log)
		self.connect()
	def open(self):
		return self._sendcmd('open=1')
	def update(self):
		return self._sendcmd('update=1')
	def exit(self):
		return self._sendcmd('exit=1')
	def getStand(self, idx):
		imgdata = receive_image(self._sendmsg('stand=1&i=%i' % idx))
		return imgdata
	def getFringes(self, i, j):
		imgdata = receive_image(self._sendmsg('fringes=1&i=%i&j=%i' % (i,j)))
		return imgdata
	def getMatrices(self):
		imgdata = receive_image(self._sendmsg('matrices=1'))
		return imgdata
	def getAllSpectra(self):
		imgdata = receive_image(self._sendmsg('all_spectra=1'))
		return imgdata
	def get(self, msg):
		imgdata = receive_image(self._sendmsg(msg))
		return imgdata

if __name__ == "__main__":
	import sys
	
	if len(sys.argv) <= 1:
		print "Usage: %s [stand i | fringes i j | matrix | spectra | exit ]" % sys.argv[0]
		sys.exit(-1)
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	config = {}
	execfile(configfile, config)
	
	port       = 6283
	host       = config['headnodehost']
	logstream  = sys.stderr
	debuglevel = 1
	
	print "Connecting to headnode vis service"
	ledavis = LEDARemoteHeadNodeVis(host, port,
	                                LEDALogger(logstream, debuglevel))
	print "Opening latest snapshot"
	ledavis.open()
	
	cmd = sys.argv[1]
	print "Requesting '%s' visualisation" % cmd
	if cmd == "stand":
		try:
			idx = int(sys.argv[2])
		except:
			print "Missing or invalid stand index"
			sys.exit(-1)
		outfilename = "stand_%i.png" % idx
		open(outfilename, 'w').write(ledavis.getStand(idx))
		print "Output written to", outfilename
		
	elif cmd == "fringes":
		try:
			i = int(sys.argv[2])
			j = int(sys.argv[3])
		except:
			print "Missing or invalid stand index"
			sys.exit(-1)
		outfilename = "fringes_%i_%i.png" % (i, j)
		open(outfilename, 'w').write(ledavis.getFringes(i, j))
		print "Output written to", outfilename
		
	elif cmd == "matrix":
		outfilename = "matrix.png"
		open(outfilename, 'w').write(ledavis.getMatrices())
		print "Output written to", outfilename
		
	elif cmd == "spectra":
		outfilename = "spectra.png"
		open(outfilename, 'w').write(ledavis.getAllSpectra())
		print "Output written to", outfilename
		
	elif cmd == "exit":
		ledavis.exit()
		print "servervis processes commanded to exit"
		
	else:
		print "Unknown command '%s'" % cmd
		sys.exit(-1)
