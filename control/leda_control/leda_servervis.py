#!/usr/bin/env python

"""

By Ben Barsdell (2013)

"""

import datetime
import os
import StringIO
from SimpleSocket import SimpleSocket
from leda_correlator_dump import correlator_dump

port = 3142

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

class LEDAVis(object):
	def __init__(self, datapaths, nchan_reduced):
		self.datapaths = datapaths
		self.data = correlator_dump()
		self.nchan_reduced = nchan_reduced
		self.visibilities = None
		
	def open_latest(self):
		""" 'Opens' latest correlator dump
		"""
		datestamps = [self.getLatestDatestamp(path) \
			              for path in self.datapaths]
		self.data.open(datestamps)
		
	def _getLatestDatestamp(self, path, rank=0):
		return sorted(glob.glob(path + "/*.dada"),
		              key=os.path.getmtime, reverse=True)[rank][:19]
	
	def update(self):
		self.visibilities = self.data.read_last()
		
	def get_visibilities(self):
		return self.visibilities

def send_array(socket, data, metadata={}):
	datastr = StringIO.StringIO()
	np.save(datastr, data)
	#socket.send(datastr.getvalue())
	metadata['data'] = datastr.getvalue()
	encoded = json.dumps(metadata)
	socket.send(encoded)

def onMessage(ledavis, message, clientsocket, address):
	args = dict([x.split('=') for x in message.split('&')])
	#print "Received:", args
	
	if 'open' in args:
		logMsg(1, DL, "Request to open")
		ledavis.open_latest()
		metadata = {'nchan':       ledavis.data.nchan,
		            'ndim':        ledavis.data.ndim,
		            'npol':        ledavis.data.npol,
		            'nstation':    ledavis.data.nstation,
		            'ninput':      ledavis.data.ninput,
		            'navg':        ledavis.data.navg,
		            'center_freq': ledavis.data.center_freq}
		clientsocket.send(json.dumps(metadata))
	elif 'update' in args:
		logMsg(1, DL, "Request to update")
		ledavis.update()
		clientsocket.send('ok')
	elif 'stand' in args:
		i = int(args['stand'])
		logMsg(1, DL, "Stand %i data requested" % (i))
		visibilities = ledavis.get_visibilities()
		powspec_x = np.real(visibilities[0,:,i,i,0,0])
		powspec_y = np.real(visibilities[0,:,i,i,1,1])
		powspec_x = 10*np.log10(powspec_x)
		powspec_y = 10*np.log10(powspec_y)
		data = numpy.array([powspec_x, powspec_y])
		send_array(clientsocket, data)
	elif 'fringes' in args:
		i = int(args['i'])
		j = int(args['j'])
		logMsg(1, DL, "Fringe data requested for baseline %i-%i" % (i,j))
		visibilities = ledavis.get_visibilities()
		fringes_xx = np.angle(visibilities[0,:,i,j,0,0])
		fringes_yy = np.angle(visibilities[0,:,i,j,1,1])
		data = numpy.array([fringes_xx, fringes_yy])
		send_array(clientsocket, data)
	elif 'matrices' in args:
		logMsg(1, DL, "Matrix data requested")
		visibilities = ledavis.get_visibilities()
		# TODO: This assumes we want to sum across the whole band
		matrix_xx = np.sum(visibilities[0,:,:,:,0,0], axis=0)
		matrix_yy = np.sum(visibilities[0,:,:,:,1,1], axis=0)
		amp_xx    = 10*np.log10(np.abs(matrix_xx))
		amp_yy    = 10*np.log10(np.abs(matrix_yy))
		phase_xx  = np.angle(matrix_xx)
		phase_yy  = np.angle(matrix_yy)
		data = numpy.array([amp_xx, amp_yy, phase_xx, phase_yy])
		send_array(clientsocket, data)
	elif 'all_spectra' in args:
		logMsg(1, DL, "All-spectra data requested")
		# TODO: It would be nice to fscrunch a little here, but
		#         due to odd nchans, it would require using
		#         something like scipy.signal.decimate
		visibilities = ledavis.get_visibilities()
		i = np.arange(visibilities.shape[2])
		powspectra_x = np.real(visibilities[0,:,i,i,0,0])
		powspectra_y = np.real(visibilities[0,:,i,i,1,1])
		
		# Reduce channel resolution (taking the max val)
		# Note: If taking avg here, need to normalise by len(sb)
		powspectra_x = np.array_split(powspectra_x, ledavis.nchan_reduced)
		powspectra_x = np.array([sb.max() for sb in powspectra_x])
		powspectra_y = np.array_split(powspectra_y, ledavis.nchan_reduced)
		powspectra_y = np.array([sb.max() for sb in powspectra_y])
		
		powspectra_x = 10*np.log10(powspectra_x)
		powspectra_y = 10*np.log10(powspectra_y)
		data = numpy.array([powspectra_x, powspectra_y])
		send_array(clientsocket, data)
	else:
		logMsg(1, DL, "Ignoring unknown message: %s" % message)
		
if __name__ == "__main__":
	import functools
	from configtools import *
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	execfile(configfile, globals())
	
	# TODO: This display parameter could be put into the config file
	nchan_reduced_max = 128
	nchan_reduced_server = nchan_reduced_max // len(serverhosts)
	ledavis = LEDAVis(disk_outpaths, nchan_reduced_server)
	
	print "Listening for client requests on port %i..." % port
	sock = SimpleSocket()
	sock.listen(functools.partial(onMessage, ledavis), port)
