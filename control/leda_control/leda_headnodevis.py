#!/usr/bin/env python

"""

By Ben Barsdell (2013)

TODO: Make (sure) the specified stands are translated into LEDA stand indices
        To make life easier, use two STANDS files: one with all positions and delays,
          and one with only LEDA-connected stands with corr and adc inds etc.
TODO: Add UTC datestamps and some header info to all plots
TODO: Add new modes: adc_stand_time, adc_stand_spectrum, adc_all_time, adc_all_spectra

"""

import StringIO
from SimpleSocket import SimpleSocket
from leda_client import LEDAClient
from leda_logger import LEDALogger
import subprocess
import corr
import base64
import json
import numpy as np
import matplotlib
matplotlib.use('Agg') # Prevent it from trying to use Xwindows backend
import matplotlib.pyplot as plt
import time
from async import AsyncCaller

g_port = 6283

def receive_array(msg):
	if msg is None or msg == "none":
		return None
	#datastr = StringIO.StringIO(msg)
	#data = np.load(datastr)
	#return data
	metadata = json.loads(msg)
	decoded_data = base64.standard_b64decode(metadata['data'])
	datastr = StringIO.StringIO(decoded_data)
	metadata['data'] = np.load(datastr)
	return metadata

class LEDARemoteVisServer(LEDAClient):
	def __init__(self, host, port, log):
		super(LEDARemoteVisServer, self).__init__(host, port, log)
		#self.connect()
	def open(self):
		ret = self._sendmsg('open=1')
		if ret is not None:
			metadata = json.loads(ret)
		else:
			metadata = {'nchan':0,'ndim':0,'npol':0,
			            'nstation':0,'ninput':0,'navg':0,
			            'center_freq':0.}
		self.nchan       = int(metadata['nchan'])
		self.ndim        = int(metadata['ndim'])
		self.npol        = int(metadata['npol'])
		self.nstation    = int(metadata['nstation'])
		self.ninput      = int(metadata['ninput'])
		self.navg        = int(metadata['navg'])
		self.center_freq = float(metadata['center_freq'])
	def update(self):
		return self._sendcmd('update=1')
	def getStand(self, idx):
		metadata = receive_array(self._sendmsg('stand=1&i=%i' % idx))
		if metadata is None:
			return None
		data = metadata['data']
		powspec_x, powspec_y = data
		return powspec_x, powspec_y
	def getFringes(self, idx_i, idx_j):
		metadata = receive_array(self._sendmsg('fringes=1&i=%i&j=%i' \
			                                       % (idx_i,idx_j)))
		if metadata is None:
			return None
		data = metadata['data']
		fringes_xx, fringes_yy = data
		return fringes_xx, fringes_yy
	def getMatrices(self):
		metadata = receive_array(self._sendmsg('matrices=1'))
		if metadata is None:
			return None
		data = metadata['data']
		amp_xx, amp_yy, phase_xx, phase_yy = data
		return amp_xx, amp_yy, phase_xx, phase_yy
	def getAllSpectra(self):
		metadata = receive_array(self._sendmsg('all_spectra=1'))
		if metadata is None:
			return None
		data = metadata['data']
		powspectra_x, powspectra_y = data
		return powspectra_x, powspectra_y
	def exit(self):
		self.log.write("Requesting server vis script to exit", 2)
		self._sendcmd("exit=1")

# TODO: Should probably just have one LEDARoach class that includes everything and is
#         in its own file, to be included here and in leda_headnodecontrol.
class LEDARoachVis(object):
	def __init__(self, host, port, log=LEDALogger()):
		self.host = host
		self.port = port
		self.log  = log
		self.ninputs = 32
		self.npol = 2
		#self.connect()
	def connect(self):
		self.log.write("Connecting to ROACH %s:%i" % (self.host,self.port))
		self.fpga = corr.katcp_wrapper.FpgaClient(self.host, self.port)
		time.sleep(2)
		if not self.fpga.is_connected():
			self.log.write("Failed to connect", -2)
			self.fpga = None
	def isConnected(self):
		return self.fpga is not None
	def getSamples(self):
		nperframe = 1024
		# Run adc16_dump_chans as a subprocess, capture the output
		sp = subprocess.Popen(["adc16_dump_chans.rb", "-l",
		                       str(nperframe), str(self.host)],
		                      stdout=subprocess.PIPE)
		output = sp.communicate()[0]
		# Parse into numpy array
		data = np.fromstring(output, sep=' ', dtype=np.int8)
		data = data.reshape((nperframe,self.ninputs/self.npol,self.npol))
		data_x, data_y = data[...,0], data[...,1]
		return data_x, data_y
	def getPowerSpectra(self):
		tdata_x, tdata_y = self.getSamples()
		fdata_x = np.fft.rfft(tdata_x, axis=0) / tdata_x.shape[0]
		fdata_y = np.fft.rfft(tdata_y, axis=0) / tdata_y.shape[0]
		powspectra_x = np.real(fdata_x*np.conj(fdata_x)).astype(np.float32)
		powspectra_y = np.real(fdata_y*np.conj(fdata_y)).astype(np.float32)
		powspectra_x = 10*np.log10(powspectra_x)
		powspectra_y = 10*np.log10(powspectra_y)
		return powspectra_x, powspectra_y
	def getSampleHists(self):
		all_samples_x, all_samples_y = self.getSamples()
		all_samples_x = all_samples_x.T
		all_samples_y = all_samples_y.T
		hists_x = [np.histogram(s, bins=15)[0] for s in all_samples_x]
		hists_y = [np.histogram(s, bins=15)[0] for s in all_samples_y]
		return hists_x, hists_y

class LEDARemoteVisManager(object):
	def __init__(self,
	             serverhosts, controlports,
	             roachhosts, roachport,
	             lowfreq, highfreq,
	             stands_x, stands_y,
	             adc2stand, leda2stand,
	             #stand2adc, stand2leda,
	             log=LEDALogger()):
		self.lowfreq   = lowfreq
		self.highfreq  = highfreq
		self.stands_x  = stands_x
		self.stands_y  = stands_y
		#self.stand2adc  = stand2adc
		#self.adc2stand  = stand2adc.argsort()
		#self.stand2leda = stand2leda
		#self.leda2stand = stand2leda.argsort()
		self.adc2stand  = adc2stand
		self.leda2stand = leda2stand
		self.log = log
		async = AsyncCaller()
		self.servers = [LEDARemoteVisServer(host,controlport,log) \
			                for controlport in controlports \
			                for host in serverhosts]
		for server in self.servers:
			async(server.connect)()
		async.wait()
		self.roaches = [LEDARoachVis(host,roachport,log) \
			                for host in roachhosts]
		for roach in self.roaches:
			async(roach.connect)()
		async.wait()
	def open(self):
		async = AsyncCaller()
		for server in self.servers:
			async(server.open)()
		async.wait()
		self.nchan = sum([server.nchan for server in self.servers])
		self.ndim = self.servers[0].ndim
		self.npol = self.servers[0].npol
		self.nstation = self.servers[0].nstation
		self.ninput = self.servers[0].ninput
		self.navg = self.servers[0].navg
		self.center_freq = sum([server.center_freq for server in self.servers]) \
		    / float(len(self.servers))
		# Sort servers by frequency
		## HACK TESTING disabled
		self.servers.sort(key=lambda s: s.center_freq)
	def update(self):
		async = AsyncCaller()
		for server in self.servers:
			async(server.update)()
		async.wait()
			#server.update()
	def exit(self):
		for server in self.servers:
			server.exit()
	#def sortByFreq(self, values):
	#	cfreqs = [server.center_freq for server in self.servers]
	#	cfreqs, values = zip(*sorted(zip(cfreqs, values)))
	def getStand(self, idx):
		# TODO: This, if still desired, requires searching for the entry
		#         and handling missing stands.
		#idx = self.stand2leda[idx]
		
		powspec_subbands_x = []
		powspec_subbands_y = []
		async = AsyncCaller()
		for server in self.servers:
			async(server.getStand)(idx)
		rets = async.wait()
		for ret in rets:
			#ret = server.getStand(idx)
			if ret is None:
				return None
			powspec_x, powspec_y = ret
			powspec_subbands_x.append(powspec_x)
			powspec_subbands_y.append(powspec_y)
		#self.sortByFreq(powspec_subbands_x)
		#self.sortByFreq(powspec_subbands_y)
		powspec_x = np.concatenate(powspec_subbands_x, axis=0)
		powspec_y = np.concatenate(powspec_subbands_y, axis=0)
		return powspec_x, powspec_y
	def getFringes(self, idx_i, idx_j):
		#idx_i = self.stand2leda[idx_i]
		#idx_j = self.stand2leda[idx_j]
		
		fringes_subbands_xx = []
		fringes_subbands_yy = []
		async = AsyncCaller()
		for server in self.servers:
			async(server.getFringes)(idx_i, idx_j)
		rets = async.wait()
		for ret in rets:
			#ret = server.getFringes(idx_i, idx_j)
			if ret is None:
				return None
			fringes_xx, fringes_yy = ret
			fringes_subbands_xx.append(fringes_xx)
			fringes_subbands_yy.append(fringes_yy)
		#self.sortByFreq(fringes_subbands_xx)
		#self.sortByFreq(fringes_subbands_yy)
		fringes_xx = np.concatenate(fringes_subbands_xx, axis=0)
		fringes_yy = np.concatenate(fringes_subbands_yy, axis=0)
		return fringes_xx, fringes_yy
	def getMatrices(self):
		amp_xx_subbands   = []
		amp_yy_subbands   = []
		phase_xx_subbands = []
		phase_yy_subbands = []
		async = AsyncCaller()
		for server in self.servers:
			async(server.getMatrices)()
		rets = async.wait()
		for ret in rets:
			#ret = server.getMatrices()
			if ret is None:
				return None
			amp_xx, amp_yy, phase_xx, phase_yy = ret
			amp_xx_subbands.append(amp_xx)
			amp_yy_subbands.append(amp_yy)
			phase_xx_subbands.append(phase_xx)
			phase_yy_subbands.append(phase_yy)
		amp_xx = np.median(np.array(amp_xx_subbands), axis=0)
		amp_yy = np.median(np.array(amp_yy_subbands), axis=0)
		phase_xx = np.median(np.array(phase_xx_subbands), axis=0)
		phase_yy = np.median(np.array(phase_yy_subbands), axis=0)
		"""
		# Sort into real stand order
		amp_xx = amp_xx[self.stand2leda, self.stand2leda]
		amp_yy = amp_yy[self.stand2leda, self.stand2leda]
		phase_xx = phase_xx[self.stand2leda, self.stand2leda]
		phase_yy = phase_yy[self.stand2leda, self.stand2leda]
		"""
		return amp_xx, amp_yy, phase_xx, phase_yy
	def getAllSpectra(self):
		powspectra_subbands_x = []
		powspectra_subbands_y = []
		async = AsyncCaller()
		for server in self.servers:
			async(server.getAllSpectra)()
		rets = async.wait()
		for ret in rets:
			#ret = server.getAllSpectra()
			if ret is None:
				return None
			powspectra_x, powspectra_y = ret
			powspectra_subbands_x.append(powspectra_x)
			powspectra_subbands_y.append(powspectra_y)
		#self.sortByFreq(powspectra_subbands_x)
		#self.sortByFreq(powspectra_subbands_y)
		powspectra_x = np.concatenate(powspectra_subbands_x, axis=0)
		powspectra_y = np.concatenate(powspectra_subbands_y, axis=0)
		"""
		# Sort into real stand order
		powspectra_x = powspectra_x[:,self.stand2leda]
		powspectra_y = powspectra_y[:,self.stand2leda]
		"""
		return powspectra_x, powspectra_y
	def getADCAllTimeSeries(self):
		timeseries_substands_x = []
		timeseries_substands_y = []
		async = AsyncCaller()
		for roach in self.roaches:
			async(roach.getSamples)()
		rets = async.wait()
		for ret in rets:
			#ret = roach.getSamples()
			if ret is None:
				return None
			timeseries_x, timeseries_y = ret
			timeseries_substands_x.append(timeseries_x)
			timeseries_substands_y.append(timeseries_y)
		# Note: This assumes the roaches and ADCs are already ordered logically
		timeseries_x = np.concatenate(timeseries_substands_x, axis=1)
		timeseries_y = np.concatenate(timeseries_substands_y, axis=1)
		"""
		# Sort by real stand number
		timeseries_x = timeseries_x[..., self.stand2adc]
		timeseries_y = timeseries_y[..., self.stand2adc]
		"""
		return timeseries_x, timeseries_y
	def getADCAllSpectra(self):
		powspectra_substands_x = []
		powspectra_substands_y = []
		async = AsyncCaller()
		for roach in self.roaches:
			async(roach.getPowerSpectra)()
		rets = async.wait()
		for ret in rets:
			#ret = roach.getPowerSpectra()
			if ret is None:
				return None
			powspectra_x, powspectra_y = ret
			powspectra_substands_x.append(powspectra_x)
			powspectra_substands_y.append(powspectra_y)
		# Note: This assumes the roaches and ADCs are already ordered logically
		powspectra_x = np.concatenate(powspectra_substands_x, axis=1)
		powspectra_y = np.concatenate(powspectra_substands_y, axis=1)
		"""
		# Sort by real stand number
		powspectra_x = powspectra_x[..., self.stand2adc]
		powspectra_y = powspectra_y[..., self.stand2adc]
		"""
		return powspectra_x, powspectra_y

def plot_none():
	plt.figure(figsize=(10.24, 7.68), dpi=100)
	plt.xlim([-1,1])
	plt.ylim([-1,1])
	plt.text(0, 0, "No data", fontsize=32)
	plt.axis('off')

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
	elif "exit" in args:
		ledavis.exit()
		clientsocket.send('ok')
	elif 'stand' in args:
		# TODO: Should probably move most of this code into plot_* methods
		#         of ledavis.
		
		idx = int(args['i'])
		ret = ledavis.getStand(idx)
		if ret is None:
			plot_none()
		else:
			powspec_x, powspec_y = ret
			
			stand_i = ledavis.leda2stand[idx]
			
			# Note: the servervis process may send < ledavis.nchan channels here
			nchan_reduced = powspec_x.shape[0]
			freqs = np.linspace(ledavis.lowfreq, ledavis.highfreq, nchan_reduced)
			
			freq_axis_padding = 0.02
			xmin = ledavis.lowfreq  * (1 - freq_axis_padding)
			xmax = ledavis.highfreq * (1 + freq_axis_padding)
			# TODO: How/where to decide these?
			ymin = 75
			ymax = 95
			nchan = powspec_x.shape[0]
			
			plt.figure(figsize=(10.24, 7.68), dpi=100)
			plt.plot(freqs, powspec_x, color='r', label="Pol A")
			plt.plot(freqs, powspec_y, color='b', label="Pol B")
			plt.xlim([xmin, xmax])
			plt.ylim([ymin, ymax])
			plt.xlabel('Frequency [MHz]')
			plt.ylabel('Power [dB]')
			plt.title('LEDA output for stand %i' % (stand_i + 1))
			plt.legend()
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
		
	elif 'fringes' in args:
		idx_i = int(args['i'])
		idx_j = int(args['j'])
		ret = ledavis.getFringes(idx_i, idx_j)
		if ret is None:
			plot_none()
		else:
			fringes_xx, fringes_yy = ret
			
			# Note: the servervis process may send < ledavis.nchan channels here
			nchan_reduced = fringes_xx.shape[0]
			freqs = np.linspace(ledavis.lowfreq, ledavis.highfreq, nchan_reduced)
			
			stand_i = ledavis.leda2stand[idx_i]
			stand_j = ledavis.leda2stand[idx_j]
			stands_x, stands_y = ledavis.stands_x.copy(), ledavis.stands_y.copy()
			# HACK to bring outriggers in closer
			stands_x[-5:] *= 0.5
			stands_y[-5:] *= 0.5
			
			plt.figure(figsize=(10.24, 7.68), dpi=100)
			plt.plot(freqs, fringes_xx, color='r')
			plt.plot(freqs, fringes_yy, color='b')
			plt.xlabel('Frequency [MHz]')
			plt.ylabel('Phase [radians]')
			plt.title('LEDA fringes for baseline %i - %i' % \
				          (stand_i+1, stand_j+1))
			# Add subplot showing stands and baseline
			ax2 = plt.axes([0.7,0.7,0.2,0.2])
			ax2.plot(stands_x, stands_y, '.', c='black', markersize=2)
			ax2.plot([stands_x[stand_i],stands_x[stand_j]],
			         [stands_y[stand_i],stands_y[stand_j]],
			         color='purple', lw=2)
			ax2.set_xticklabels(())
			ax2.set_yticklabels(())
			ax2.set_xticks(())
			ax2.set_yticks(())
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
		
	elif 'matrices' in args:
		ret = ledavis.getMatrices()
		if ret is None:
			plot_none()
		else:
			amp_xx, amp_yy, phase_xx, phase_yy = ret
			
			# TODO: How to label real stand numbers here?
			
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
		
		ret = ledavis.getAllSpectra()
		if ret is None:
			plot_none()
		else:
			powspectra_x, powspectra_y = ret
			
			xmin = ledavis.lowfreq
			xmax = ledavis.highfreq
			ymin = 75
			ymax = 95
			
			du = 1.1 * (xmax-xmin)
			dv = 1.1 * (ymax-ymin)
			
			#stands = ledavis.stands
			stands_x, stands_y = ledavis.stands_x.copy(), ledavis.stands_y.copy()
			stands_x_max = np.abs(stands_x).max()
			stands_y_max = np.abs(stands_y).max()
			# HACK to bring outriggers in closer
			stands_x[-5:] *= 0.5
			stands_y[-5:] *= 0.5
			
			plt.figure(figsize=(10.24, 7.68), dpi=100)
			plt.axis('off')
			
			# Note: the servervis process may send < ledavis.nchan channels here
			nchan_reduced = powspectra_x.shape[0]
			freqs = np.linspace(ledavis.lowfreq, ledavis.highfreq, nchan_reduced)
			
			ntile = 16
			for v in range(ledavis.nstation / ntile):
				for u in range(ntile):
					i = u + v*ntile
					powspec_x = powspectra_x[:,i]
					powspec_y = powspectra_y[:,i]
					# TODO: These have already been done on the server
					#powspec_x = 10*np.log10(powspec_x)
					#powspec_y = 10*np.log10(powspec_y)
					# Saturate values to visible range for better visualisation
					powspec_x[powspec_x < ymin] = ymin
					#powspec_x[powspec_x > ymax] = ymax
					powspec_y[powspec_y < ymin] = ymin
					#powspec_y[powspec_y > ymax] = ymax
					
					stand_i = ledavis.leda2stand[i]
					x = stands_x[stand_i] / stands_x_max * ntile
					y = stands_y[stand_i] / stands_y_max * ntile
					plt.plot(freqs + x*du, powspec_x + y*dv, color='r', linewidth=0.5)
					plt.plot(freqs + x*du, powspec_y + y*dv, color='b', linewidth=0.5)
					#plt.text(xmin+0.2*(xmax-xmin) + x*du, ymin+y*dv, str(j),
					#         fontsize=8, fontweight='black', color='white')
					plt.text(xmin+0.2*(xmax-xmin) + x*du, ymin-0.45*(ymax-ymin)+y*dv,
					         # Note: i here is (0-based) real stand index
							 stand_i + 1,
							 fontsize=6, color='black')
							 #fontsize=8, fontweight='heavy', color='black')
					
			plt.xlim([-du*18, du*15])
			plt.ylim([-dv*11, dv*22])
			
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)
	
	elif 'adc_all_spectra' in args:
		ret = ledavis.getADCAllSpectra()
		if ret is None:
			plot_none()
		else:
			powspectra_x, powspectra_y = ret
			
			xmin = ledavis.lowfreq
			xmax = ledavis.highfreq
			ymin = 75
			ymax = 95
			
			du = 1.1 * (xmax-xmin)
			dv = 1.1 * (ymax-ymin)
			
			plt.figure(figsize=(10.24, 7.68), dpi=100)
			plt.axis('off')
			
			nchan_reduced = powspectra_x.shape[0]
			freqs = np.linspace(ledavis.lowfreq, ledavis.highfreq, nchan_reduced)
			
			ntile = 16
			for v in range(ledavis.nstation / ntile):
				for u in range(ntile):
					i = u + v*ntile
					powspec_x = powspectra_x[:,i]
					powspec_y = powspectra_y[:,i]
					# Saturate values to visible range for better visualisation
					powspec_x[powspec_x < ymin] = ymin
					powspec_y[powspec_y < ymin] = ymin
					
					stand_i = ledavis.adc2stand[i]
					plt.plot(freqs + u*du, powspec_x + v*dv, color='r', linewidth=0.5)
					plt.plot(freqs + u*du, powspec_y + v*dv, color='b', linewidth=0.5)
					plt.text(xmin + u*du, ymin + v*dv,
					         # Note: i here is (0-based) real stand index
							 stand_i + 1,
							 fontsize=6, color='black')
					
		imgfile = StringIO.StringIO()
		plt.savefig(imgfile, format='png', bbox_inches='tight')
		plt.close()
		imgdata = imgfile.getvalue()
		send_image(clientsocket, imgdata)

if __name__ == "__main__":
	import sys
	from configtools import *
	import functools
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	execfile(configfile, globals())
	
	logstream   = sys.stderr
	debuglevel  = 1
	
	df       = corr_clockfreq / float(corr_nfft)
	highfreq = lowfreq + df*nchan*len(serverhosts)*nstream
	
	stands, stands_x, stands_y = \
	    np.loadtxt(site_stands_file, usecols=[0,1,2], unpack=True)
	# Sort into proper stand order
	stands = stands.astype(np.int32)
	inds = stands.argsort()
	stands_x = stands_x[inds]
	stands_y = stands_y[inds]
	
	stands, roaches, adcs, adc_inds, leda_inds = \
	    np.loadtxt(leda_stands_file, usecols=[0,1,2,3,4], unpack=True)
	# Convert from 1-based to 0-based indexing
	stands    = stands.astype(np.int32) - 1
	roaches   = roaches.astype(np.int32) - 1
	adcs      = adcs.astype(np.int32) - 1
	adc_inds  = adc_inds.astype(np.int32) - 1
	leda_inds = leda_inds.astype(np.int32) - 1
	# Sort into stand order
	#inds = stands.argsort()
	inds = leda_inds.argsort()
	leda2stand = stands[inds]
	
	adc_inds = adc_inds + 8*(adcs + 2*(roaches))
	inds = adc_inds.argsort()
	adc2stand = stands[inds]
	"""
	roaches    = roaches[inds]
	adcs       = adcs[inds]
	adc_inds   = adc_inds[inds]
	leda_inds  = leda_inds[inds]
	stand2leda = stand2leda[inds]
	stand2adc  = adc_inds + 8*(adcs + 2*(roaches))
	"""
	"""
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
	"""
	ledavis = LEDARemoteVisManager(serverhosts, visports,
	                               roachhosts, roachport,
	                               lowfreq, highfreq,
	                               stands_x, stands_y,
	                               #stand2adc, stand2leda,
	                               adc2stand, leda2stand,
	                               LEDALogger(logstream, debuglevel))
	
	print "Listening for client requests on port %i..." % g_port
	sock = SimpleSocket()
	sock.listen(functools.partial(onMessage, ledavis), g_port)
