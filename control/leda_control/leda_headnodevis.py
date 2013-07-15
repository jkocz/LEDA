#!/usr/bin/env python

"""

By Ben Barsdell (2013)

"""

import StringIO
from SimpleSocket import SimpleSocket
from leda_client import LEDAClient
from leda_logger import LEDALogger
import base64
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import time

g_port = 6283

def receive_array(msg):
	metadata = json.loads(msg)
	datastr = StringIO.StringIO(metadata['data'])
	metadata['data'] = np.load(datastr)
	return metadata

class LEDARemoteVisServer(LEDAClient):
	def __init__(self, host, port, log):
		super(LEDARemoteVisServer, self).__init__(host, port, log)
		self.connect()
	def open(self):
		metadata = json.loads(self._sendmsg('open=1'))
		self.nchan       = metadata['nchan']
		self.ndim        = metadata['ndim']
		self.npol        = metadata['npol']
		self.nstation    = metadata['nstation']
		self.ninput      = metadata['ninput']
		self.navg        = metadata['navg']
		self.center_freq = metadata['center_freq']
	def update(self):
		self._sendcmd('update=1')
	def getStand(self, idx):
		metadata = receive_array(self._sendmsg('stand=%i' % idx))
		data = metadata['data']
		powspec_x, powspec_y = data
		return powspec_x, powspec_y
	def getFringes(self, idx_i, idx_j):
		data = receive_array(self._sendmsg('fringes=1&i=%i&j=%j' \
			                                   % (idx_i,idx_j)))
		fringes_xx, fringes_yy = data
		return fringes_xx, fringes_yy
	def getMatrices(self):
		data = receive_array(self._sendmsg('matrices'))
		amp_xx, amp_yy, phase_xx, phase_yy = data
		return amp_xx, amp_yy, phase_xx, phase_yy
	def getAllSpectra(self):
		data = receive_array(self._sendmsg('all_spectra'))
		powspectra_x, powspectra_y = data
		return powspectra_x, powspectra_y

class LEDARemoteVisManager(object):
	def __init__(self, serverhosts, controlport,
	             lowfreq, highfreq,
	             stands, stands_x, stands_y,
	             log=LEDALogger()):
		self.lowfreq  = lowfreq
		self.highfreq = highfreq
		self.stands   = stands
		self.stands_x = stands_x
		self.stands_y = stands_y
		self.log = log
		self.servers = [LEDARemoveVisServer(host,controlport,log) \
			                for host in serverhosts]
	def open(self):
		for server in self.servers:
			server.open()
		self.nchan = sum([server.nchan for server in self.servers])
		self.ndim = self.servers[0].ndim
		self.npol = self.servers[0].npol
		self.nstation = self.servers[0].nstation
		self.ninput = self.servers[0].ninput
		self.navg = self.servers[0].navg
		self.center_freq = sum([server.center_freq for server in self.servers]) \
		    / float(len(self.servers))
		
		self.freqs = np.linspace(self.lowfreq, self.highfreq, self.nchan)
	def sortByFreq(self, values):
		cfreqs = [server.center_freq for server in self.servers]
		cfreqs, values = zip(*sorted(zip(cfreqs, values)))
	def getStand(self, idx):
		powspec_subbands_x = []
		powspec_subbands_y = []
		for server in self.servers:
			powspec_x, powspec_y = server.getStand(idx)
			powspec_subbands_x.append(powspec_x)
			powspec_subbands_y.append(powspec_y)
		self.sortByFreq(powspec_subbands_x)
		self.sortByFreq(powspec_subbands_y)
		powspec_x = np.concatenate(powspec_subbands_x, axis=0)
		powspec_y = np.concatenate(powspec_subbands_y, axis=0)
		return powspec_x, powspec_y
	def getFringes(self, idx_i, idx_j):
		fringes_subbands_xx = []
		fringes_subbands_yy = []
		for server in self.servers:
			fringes_x, fringes_y = server.getFringes(idx_i, idx_j)
			fringes_subbands_xx.append(fringes_xx)
			fringes_subbands_yy.append(fringes_yy)
		self.sortByFreq(fringes_subbands_xx)
		self.sortByFreq(fringes_subbands_yy)
		fringes_xx = np.concatenate(fringes_subbands_xx, axis=0)
		fringes_yy = np.concatenate(fringes_subbands_yy, axis=0)
		return fringes_xx, fringes_yy
	def getMatrices(self):
		amp_xx_subbands   = []
		amp_yy_subbands   = []
		phase_xx_subbands = []
		phase_yy_subbands = []
		for server in self.servers:
			amp_xx, amp_yy, phase_xx, phase_yy = server.getMatrices()
			amp_xx_subbands.append(amp_xx)
			amp_yy_subbands.append(amp_yy)
			phase_xx_subbands.append(phase_xx)
			phase_yy_subbands.append(phase_yy)
		amp_xx = numpy.array(amp_xx_subbands).sum(axis=0)
		amp_yy = numpy.array(amp_yy_subbands).sum(axis=0)
		phase_xx = numpy.array(phase_xx_subbands).sum(axis=0)
		phase_yy = numpy.array(phase_yy_subbands).sum(axis=0)
		return amp_xx, amp_yy, phase_xx, phase_yy
	def getAllSpectra(self):
		powspectra_subbands_x = []
		powspectra_subbands_y = []
		for server in self.servers:
			powspectra_x, powspectra_y = server.getAllSpectra(idx)
			powspectra_subbands_x.append(powspectra_x)
			powspectra_subbands_y.append(powspectra_y)
		self.sortByFreq(powspectra_subbands_x)
		self.sortByFreq(powspectra_subbands_y)
		powspectra_x = np.concatenate(powspectra_subbands_x, axis=0)
		powspectra_y = np.concatenate(powspectra_subbands_y, axis=0)
		return powspectra_x, powspectra_y

def send_image(socket, imgdata):
	encoded_image = base64.standard_b64encode(imgdata)
	socket.send(encoded_image)

def onMessage(ledavis, message, clientsocket, address):
	args = dict([x.split('=') for x in message.split('&')])
	
	if 'open' in args:
		ledavis.open()
		clientsocket.send('ok')
	elif 'update' in args:
		ledavis.update()
		clientsocket.send('ok')
	elif 'stand' in args:
		# TODO: Should probably move most of this code into plot_* methods
		#         of ledavis.
		
		idx = int(args['stand'])
		powspec_x, powspec_y = ledavis.getStand(idx)
		
		freq_padding = 0.02
		xmin = ledavis.lowfreq  * (1 - freq_padding)
		xmax = ledavis.highfreq * (1 + freq_padding)
		# TODO: How/where to decide these?
		ymin = 75
		ymax = 95
		nchan = powspec_x.shape[0]
		
		plt.figure(figsize=(10.24, 7.68), dpi=100)
		plt.plot(ledavis.freqs, powspec_x, color='r', label="Pol A")
		plt.plot(ledavis.freqs, powspec_y, color='b', label="Pol B")
		plt.xlim([xmin, xmax])
		plt.ylim([ymin, ymax])
		plt.xlabel('Frequency [MHz]')
		plt.ylabel('Power [dB]')
		plt.legend()
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
		
	elif 'fringes' in args:
		idx_i = int(args['i'])
		idx_j = int(args['j'])
		fringes_xx, fringes_yy = ledavis.getFringes(idx_i, idx_j)
		
		plt.figure(figsize=(10.24, 7.68), dpi=100)
		plt.plot(ledavis.freqs, fringes_xx, color='r')
		plt.plot(ledavis.freqs, fringes_yy, color='b')
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
		
	elif 'matrices' in args:
		amp_xx, amp_yy, phase_xx, phase_yy = ledavis.getMatrices()
		
		# TODO: How/where to decide these?
		ymin = 60
		ymax = 130
		
		plt.figure(figsize=(10.24, 7.68), dpi=100)
		
		plt.subplot(2,2,1)
		plt.imshow(amp_xx, vmin=ymin, vmax=ymax,
				   extent=(0.5,ledavis.nstation+0.5,ledavis.nstation+0.5,0.5),
				   cmap=plt.cm.Blues, interpolation='nearest')
		plt.title("Amplitude XX")
		#plt.colorbar()
		plt.axis([0.5,ledavis.nstation+0.5,0.5,ledavis.nstation+0.5])
		
		plt.subplot(2,2,3)
		plt.imshow(phase_xx, vmin=-3.1415927, vmax=3.1415927,
				   extent=(0.5,ledavis.nstation+0.5,ledavis.nstation+0.5,0.5),
				   cmap=plt.cm.RdBu, interpolation='nearest')
		plt.title("Phase XX")
		#plt.colorbar()
		plt.axis([0.5,ledavis.nstation+0.5,0.5,ledavis.nstation+0.5])
		
		plt.subplot(2,2,2)
		plt.imshow(amp_yy, vmin=ymin, vmax=ymax,
				   extent=(0.5,ledavis.nstation+0.5,ledavis.nstation+0.5,0.5),
				   cmap=plt.cm.Blues, interpolation='nearest')
		plt.title("Amplitude YY")
		plt.colorbar()
		plt.axis([0.5,ledavis.nstation+0.5,0.5,ledavis.nstation+0.5])
		
		plt.subplot(2,2,4)
		plt.imshow(phase_yy, vmin=-3.1415927, vmax=3.1415927,
				   extent=(0.5,ledavis.nstation+0.5,ledavis.nstation+0.5,0.5),
				   cmap=plt.cm.RdBu, interpolation='nearest')
		plt.title("Phase YY")
		plt.colorbar()
		plt.axis([0.5,ledavis.nstation+0.5,0.5,ledavis.nstation+0.5])
		
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
		
	elif 'all_spectra' in args:
		# Plot spectra at physical locations of stands
		
		powspectra_x, powspectra_y = ledavis.getAllSpectra()
		
		xmin = ledavis.lowfreq
		xmax = ledavis.highfreq
		ymin = 75
		ymax = 95
		
		du = 1.1 * (xmax-xmin)
		dv = 1.1 * (ymax-ymin)
		
		stands = ledavis.stands
		stands_x, stands_y = ledavis.stands_x, ledavis.stands_y
		stands_x_max = np.abs(stands_x).max()
		stands_y_max = np.abs(stands_y).max()
		"""
		# HACK to bring outriggers in closer
		stands_x[251:256] *= 0.5
		stands_y[251:256] *= 0.5
		"""
		plt.figure(figsize=(10.24, 7.68), dpi=100)
		plt.axis('off')
		
		ntile = 16
		for v in range(ledavis.nstation / ntile):
			for u in range(ntile):
				i = u + v*ntile
				powspec_x = powspectra_x[:,i]
				powspec_y = powspectra_y[:,i]
				powspec_x = 10*np.log10(powspec_x)
				powspec_y = 10*np.log10(powspec_y)
				# Saturate values to visible range for better visualisation
				powspec_x[powspec_x < ymin] = ymin
				#powspec_x[powspec_x > ymax] = ymax
				powspec_y[powspec_y < ymin] = ymin
				#powspec_y[powspec_y > ymax] = ymax
				
				x = stands_x[j] / stands_x_max * ntile
				y = stands_y[j] / stands_y_max * ntile
				plt.plot(freqs + x*du, powspec_x + y*dv, color='r', linewidth=0.5)
				plt.plot(freqs + x*du, powspec_y + y*dv, color='b', linewidth=0.5)
				#plt.text(xmin+0.2*(xmax-xmin) + x*du, ymin+y*dv, str(j),
				#         fontsize=8, fontweight='black', color='white')
				plt.text(xmin+0.2*(xmax-xmin) + x*du, ymin-0.45*(ymax-ymin)+y*dv,
						 stands[i],
						 fontsize=6, color='black')
						 #fontsize=8, fontweight='heavy', color='black')
				
		plt.xlim([-du*18, du*15])
		plt.ylim([-dv*11, dv*22])
		
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)

if __name__ == "__main__":
	from configtools import *
	import functools
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	execfile(configfile, globals())
	
	controlport = 3142
	logstream   = sys.stderr
	debuglevel  = 1
	
	df     = corr_clockfreq / float(corr_nfft)
	hifreq = lowfreq + df*nchan*len(serverhosts)
	
	# Note: Loaded cols are LEDAST, STAND, POSX, POSY
	leda_stands, stands, stands_x, stands_y = \
	    np.loadtxt(stands_file, usecols=[11,0,1,2], unpack=True)
	# Filter out invalid stands
	valid = (leda_stands != 0)
	leda_stands = leda_stands[valid]
	stands   = stands[valid]
	stands_x = stands_x[valid]
	stands_y = stands_y[valid]
	# Sort by LEDA stand index
	inds = leda_stands.argsort()
	stands = stands[inds]
	stands_x  = stands_x[inds]
	stands_y  = stands_y[inds]
	
	ledavis = LEDARemoteVisManager(serverhosts, controlport,
	                               lowfreq, highfreq,
	                               stands, stands_x, stands_y,
	                               LEDALogger(logstream, debuglevel))
	
	print "Listening for client requests on port %i..." % g_port
	sock = SimpleSocket()
	sock.listen(functools.partial(onMessage, ledavis), g_port)
