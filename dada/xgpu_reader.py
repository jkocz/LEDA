
import numpy as np

# Lower triangular indexing functions, for mapping
#   baseline_idx <--> (station_i, station_j) {where i >= j}
# Note: If these are needed repeatedly, it may be worth
#         using them to pre-calculate indexing tables.
def stations(baselineid):
	row = (-0.5 + np.sqrt(0.25 + 2*baselineid)).astype(np.uint32)
	col = baselineid - row*(row+1)/2
	return row, col
def bid(station_i, station_j):
	if np.any(station_j > station_i):
		raise IndexError("Invalid index order; must have i >= j")
	return station_i*(station_i+1)/2 + station_j

class XGPUReader(object):
	"""Provides the method:
	
	process(rawdata)
	
	that converts raw XGPU output into an array of lower-triangular
	baselines (including diagonal terms) with
	  shape=(nbin, nbaseline, nchan, npol, npol)
	  dtype=np.complex64
	where nbaseline = nstation*(nstation+1)/2.
	
	E.g.,
	  xgpu_reader = XGPUReader(inbuf.header)
	  while not inbuf.eod:
	      rawdata = inbuf.read_buffer()
	      data = xgpu_reader.process(rawdata)
	      # Do stuff with data...
	"""
	TRIANGULAR_ORDER               = 0
	REAL_IMAG_TRIANGULAR_ORDER     = 1
	REGISTER_TILE_TRIANGULAR_ORDER = 2
	def __init__(self, headerdict):
		header = headerdict
		try:
			self.nbin = int(header['NBIN'])
		except KeyError:
			self.nbin = 1
		self.nchan    = int(header['NCHAN'])
		self.nstation = int(header['NSTATION'])
		self.npol     = int(header['NPOL'])
		self.ndim     = int(header['NDIM'])
		self.nbit     = int(header['NBIT'])
		self.orderstr = header['DATA_ORDER']
		self.nbaseline = self.nstation*(self.nstation+1)/2
		
		if self.nbit != 32:
			raise ValueError("Unsupported nbit (%i); must be 32" % self.nbit)
		
		if self.ndim == 2:
			self.dtype = np.complex64
		else:
			raise ValueError("Invalid ndim (%i); must be 2" % self.ndim)
		
		# Note: This dynamically sets the self.process method to point
		#         to a specific process_* method.
		if self.orderstr.find('TRIANGULAR') == 0:
			self.order = XGPUReader.TRIANGULAR_ORDER
			self.process = self.process_triangular
		elif self.orderstr.find('REAL_IMAG_TRIANGULAR') == 0:
			self.order = XGPUReader.REAL_IMAG_TRIANGULAR_ORDER
			self.process = self.process_real_imag_triangular
		elif self.orderstr.find('REG_TILE_TRIANGULAR') == 0:
			self.order = XGPUReader.REGISTER_TILE_TRIANGULAR_ORDER
			self.process = self.process_reg_tile_triangular
			# Parse out the tile dimensions if present
			xind = self.orderstr.find('x')
			if xind >= 0:
				# Note: Assumes single-digit tile dimensions
				self.tilew = int(self.orderstr[xind-1])
				self.tileh = int(self.orderstr[xind+1])
			else:
				# Assume default tile size
				self.tilew = 2
				self.tileh = 2
			# Generate table mapping tri_ind --> rtt_ind
			rtt_nbaseline = self.reg_tile_triangular_nbaseline()
			rtt_inds      = np.arange(rtt_nbaseline, dtype=np.int32)
			rtt_i, rtt_j  = self.reg_tile_triangular_stations(rtt_inds)
			valid = (rtt_i >= rtt_j)
			rtt_stations  = (rtt_i[valid], rtt_j[valid])
			rtt_bids      = bid(*rtt_stations)
			# Now we invert the mapping using a scatter
			self.bid_rtts = np.zeros(self.nbaseline, dtype=np.int32)
			# Note: This is a many-to-one scatter, but degenerate indices all
			#         correspond to the same baseline, so we don't care
			#         which end up winning the race conditions.
			self.bid_rtts[rtt_bids] = rtt_inds
		else:
			raise ValueError("Unknown data order '%s'" % self.orderstr)
	
	def process_triangular(self, rawdata):
		# Note: rawdata is ordered (nbin, nchan, nbaseline, npol, npol, ndim)
		rawshape = (self.nbin,self.nchan,self.nbaseline,self.npol,self.npol)
		
		print "rawshape:", rawshape
		size = reduce(lambda a,b:a*b, rawshape, 1) * (np.dtype(self.dtype).itemsize)
		print "bytes:", size
		"""
		# HACK TESTING **********
		rawdata = rawdata[:size]
		"""
		
		data = rawdata.view(dtype=self.dtype).reshape(rawshape)
		data = np.transpose(data, [0,2,1,3,4]) # Swap order of baseline/chan
		return data
	def process_real_imag_triangular(self, rawdata):
		# Note: rawdata is ordered (ndim, nchan, nbaseline, npol, npol)
		rawshape = (2,self.nbin,self.nchan,self.nbaseline,self.npol,self.npol)
		data = rawdata.view(dtype=np.float32).reshape(rawshape)
		data = data[0] + 1j*data[1] # Combine components into complex
		data = np.transpose(data, [0,2,1,3,4]) # Swap order of baseline/chan
		return data
	def process_reg_tile_triangular(self, rawdata):
		# Note: rawdata is ordered (ndim, nchan, rtt_nbaseline, npol, npol)
		nbaseline = self.reg_tile_triangular_nbaseline()
		rawshape = (2,self.nbin,self.nchan,nbaseline,self.npol,self.npol)
		print 'rawshape: ', rawshape
		print 'data size:', rawdata.view(dtype=np.float32).size
		data = rawdata.view(dtype=np.float32).reshape(rawshape)
		data = data[0] + 1j*data[1] # Combine components into complex
		data = data[:,:,self.bid_rtts,:,:] # Extract triangular baselines
		data = np.transpose(data, [0,2,1,3,4]) # Swap order of baseline/chan
		return data
	
	def reg_tile_triangular_nbaseline(self):
		# TODO: These may be the wrong way around (not currently an issue)
		reg_rows = self.tilew
		reg_cols = self.tileh
		return (self.nstation/reg_rows+1) * \
		    (self.nstation/reg_cols/2) * \
		    reg_rows*reg_cols
	def reg_tile_triangular_stations(self, rtt_idx):
		# TODO: These may be the wrong way around (not currently an issue)
		reg_rows = self.tilew
		reg_cols = self.tileh
		reg_tile_nbaseline = (self.nstation/reg_rows+1)*(self.nstation/reg_cols/2)
		rem = rtt_idx
		reg_col = rem / (reg_rows*reg_tile_nbaseline)
		rem %= (reg_rows*reg_tile_nbaseline)
		reg_row = rem / (reg_tile_nbaseline)
		rem %= (reg_tile_nbaseline)
		# Tiles have triangular ordering
		tile_row, tile_col = stations(rem)
		
		row = reg_row + reg_cols*tile_row
		col = reg_col + reg_rows*tile_col
		
		return row, col
