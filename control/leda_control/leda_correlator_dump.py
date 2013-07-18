
import numpy as np
import glob

def lookup_warn(table, key, default=None):
	try:
		return table[key]
	except KeyError:
		if default is not None:
			print "#Warning: No key '%s'; using default value of %s" \
			    % (key, default)
			return default
		else:
			print "#Warning: No key '%s'" % key
			return None

# Wraps a collection of sub-bands comprising a complete correlator dump
# Note: Assumes sub-bands span contiguous range of frequencies (in any order)
class correlator_dump(object):
	def __init__(self):
		self.subbands = []
	def open(self, datestamps, header_sizes=None, extensions=None):
		# Allow parameters to be singular values or lists
		if isinstance(datestamps, basestring):
			datestamps = [datestamps]
		if isinstance(header_sizes, int):
			header_sizes = [header_sizes]
		if isinstance(extensions, basestring):
			extensions = [extensions]
		if header_sizes is None:
			header_sizes = [None] * len(datestamps)
		if extensions is None:
			extensions = [None] * len(datestamps)
		self.subbands = []
		for datestamp, header_size, extension \
			    in zip(datestamps,header_sizes,extensions):
			subband = correlator_subband_dump()
			subband.open(datestamp, header_size, extension)
			self.subbands.append(subband)
			self.subbands.sort(key=lambda a: a.center_freq)
			
		self.nchan    = sum([sb.nchan for sb in self.subbands])
		# Note: Assumes all subbands have matching params
		self.nbit     = self.subbands[0].nbit
		self.ndim     = self.subbands[0].ndim
		self.npol     = self.subbands[0].npol
		self.nstation = self.subbands[0].nstation
		self.ninput   = self.subbands[0].ninput
		self.navg     = self.subbands[0].navg
		self.center_freq = sum([sb.center_freq for sb in self.subbands]) \
		    / float(len(self.subbands))
		
	def read(self, first_int, nint=1):
		if len(self.subbands) == 0:
			return None
		subbands = [sb.read(first_int, nint) for sb in self.subbands]
		if any([sb is None for sb in subbands]):
			return None
		fullmatrix = np.concatenate(subbands, axis=1)
		return fullmatrix
	def read_last(self):
		if len(self.subbands) == 0:
			return None
		subbands = [sb.read_last() for sb in self.subbands]
		if any([sb is None for sb in subbands]):
			return None
		fullmatrix = np.concatenate(subbands, axis=1)
		return fullmatrix

# Represents one sub-band of a correlator dump
class correlator_subband_dump(object):
	DEFAULT_HEADER_SIZE = 4096
	def __init__(self):
		pass
	def open(self, datestamp, header_size=None, extension=None):
		if header_size is None:
			header_size = self.DEFAULT_HEADER_SIZE
		if extension is None:
			extension = 'dada'
		byte_offset = 0
		self.datestamp = datestamp
		self.extension = extension
		self.header_size = header_size
		filename = datestamp + "_%016i.000000.%s" % (byte_offset, extension)
		f = open(filename, 'rb')
		headerstr = f.read(header_size)
		self.parse_header(headerstr)
		f.seek(0, 2)
		self.bytes_per_file = f.tell() - self.header_size
		f.close()
		
	def parse_header(self, headerstr):
		header = {}
		for line in headerstr.split('\n'):
			try:
				key, value = line.split()
			except ValueError:
				break
			key = key.strip()
			value = value.strip()
			header[key] = value
		self.header = header
		self.center_freq = float(lookup_warn(header, 'CFREQ', 0.))
		#self.bandwidth   = float(lookup_warn(header, 'BW', 14.4))
		self.nchan = int(header['NCHAN'])
		self.npol = int(header['NPOL'])
		try:
			self.nstation = int(header['NSTAND'])
		except KeyError:
			self.nstation = int(lookup_warn(header, 'NSTATION', 32))
		self.ninput = self.nstation * self.npol
		self.ndim = int(header['NDIM'])
		self.nbit = int(header['NBIT'])
		self.dtype =  \
		    np.float32 if self.nbit == 32 else \
		    np.int16 if self.nbit == 16 else \
		    np.int8 if self.nbit == 8 else \
		    None
		self.navg = int(lookup_warn(header, 'NAVG', 25*8192))
		self.bytes_per_avg = int(lookup_warn(header, 'BYTES_PER_AVG', 10444800))
		self.data_order = lookup_warn(header, 'DATA_ORDER',
		                              'REG_TILE_TRIANGULAR_2x2')
		# TODO: Refactor this into a separate function
		if self.data_order == 'REG_TILE_TRIANGULAR_2x2':
			reg_rows = 2
			reg_cols = 2
			self.matlen  = self.reg_tile_triangular_matlen(reg_rows, reg_cols)
			# Build lookup table to map matrix idx --> row/col
			self.matrows = np.zeros(self.matlen, dtype=np.uint32)
			self.matcols = np.zeros(self.matlen, dtype=np.uint32)
			for i in xrange(self.matlen):
				row, col = self.reg_tile_triangular_coords(i, reg_rows, reg_cols)
				self.matrows[i] = row
				self.matcols[i] = col
		else:
			raise KeyError("Unsupported data order '%s'" % self.data_order)
		
	def read_last(self):
		# TODO: This assumes the files always contain at least one complete integration
		last_file = sorted(glob.glob(self.datestamp + "*.dada"), reverse=True)[0]
		f = open(last_file, 'rb')
		f.seek(0, 2)
		file_size = f.tell() - self.header_size
		file_nints = file_size // self.bytes_per_avg
		if file_nints == 0:
			return None
		file_offset = (file_nints-1) * self.bytes_per_avg
		nbytes = self.bytes_per_avg
		f.seek(self.header_size + file_offset, 0)
		data = np.fromfile(f, dtype=np.uint8, count=nbytes)
		f.close()
		return self.transform_raw_data(data, 1)
		
	def read(self, first_int, nint=1):
		"""
		Returns the specified integrations as a numpy array with shape:
		(nint, nchans, nstation, nstation, npol, npol), dtype=complex64
		"""
		byte_offset = first_int * self.bytes_per_avg
		nbytes      = nint * self.bytes_per_avg
		nelements   = nbytes / (self.nbit/8)
		
		file_idx    = byte_offset // self.bytes_per_file
		file_offset = byte_offset % self.bytes_per_file
		file_byte_label = file_idx * self.bytes_per_file
		filename = self.datestamp + "_%016i.000000.%s" % (file_byte_label,
		                                                  self.extension)
		print "#Reading", filename
		f = open(filename, 'rb')
		f.seek(self.header_size + file_offset)
		# Note: We load as raw bytes to allow arbitrary file boundaries
		data = np.fromfile(f, dtype=np.uint8, count=nbytes)
		#data = np.fromfile(f, dtype=self.dtype, count=nelements)
		f.close()
		# Continue to read data from subsequent files as necessary
		while data.size < nbytes:
		#while data.size < nelements:
			file_idx += 1
			file_offset = 0
			file_byte_label = file_idx * self.bytes_per_file
			filename = self.datestamp + "_%016i.000000.%s" % (file_byte_label,
			                                                  self.extension)
			print "#Reading", filename
			f = open(filename, 'rb')
			f.seek(self.header_size + file_offset)
			new_data = fromfile(f, dtype=np.uint8, count=nbytes-data.size)
			#new_data = fromfile(f, dtype=self.dtype, count=nelements-data.size)
			data = data.append(new_data)
			f.close()
		return self.transform_raw_data(data, nint)
	
	def transform_raw_data(self, data, nint):
		# Transform raw correlator data into a sensible format
		# TODO: This may break if system endianness is different
		data = data.view(dtype=self.dtype).astype(np.float32)
		# Note: The real and imag components are stored separately
		data = data.reshape((nint, 2, self.nchan, self.matlen))
		data = data[...,0,:,:] + np.complex64(1j) * data[...,1,:,:]
		# TODO: Add support for outputting in upper/lower triangular format
		# Scatter values into new full matrix
		fullmatrix = np.zeros((nint, self.nchan,
		                       self.ninput, self.ninput),
		                      dtype=np.complex64)
		fullmatrix[..., self.matrows, self.matcols] = data
		# Fill out the other (conjugate) triangle
		tri_inds = np.arange(self.ninput*(self.ninput+1)/2, dtype=np.uint32)
		rows, cols = self.triangular_coords(tri_inds)
		fullmatrix[..., cols, rows] = np.conj(fullmatrix[..., rows, cols])
		
		# Reorder so that pol products change fastest
		fullmatrix = fullmatrix.reshape(nint, self.nchan,
		                                self.nstation, self.npol,
		                                self.nstation, self.npol)
		fullmatrix = fullmatrix.transpose([0,1,2,4,3,5])
		
		return fullmatrix
	
	def triangular_coords(self, matrix_idx):
		row = (-0.5 + np.sqrt(0.25 + 2*matrix_idx)).astype(np.uint32)
		col = matrix_idx - row*(row+1)/2
		return row, col
	
	def reg_tile_triangular_matlen(self, reg_rows, reg_cols):
		return (self.nstation/reg_rows+1) * \
		    (self.nstation/reg_cols/2) * \
		    self.npol**2*reg_rows*reg_cols
	
	def reg_tile_triangular_coords(self, matrix_idx, reg_rows, reg_cols):
		npol = self.npol
		reg_tile_nbaseline = (self.nstation/reg_rows+1)*(self.nstation/reg_cols/2)
		rem = matrix_idx
		reg_col = rem / (reg_rows*reg_tile_nbaseline*npol*npol)
		rem %= (reg_rows*reg_tile_nbaseline*npol*npol)
		reg_row = rem / (reg_tile_nbaseline*npol*npol)
		rem %= (reg_tile_nbaseline*npol*npol)
		tile_row, tile_col = self.triangular_coords(rem / (npol*npol))
		rem %= (npol*npol)
		pol_col = rem / npol
		rem %= npol
		pol_row = rem
		
		row = pol_col + npol*(reg_row + reg_cols*tile_row)
		col = pol_row + npol*(reg_col + reg_rows*tile_col)
		
		return row, col
