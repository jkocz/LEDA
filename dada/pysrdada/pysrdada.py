#!/usr/bin/env python

import numpy
#import struct
import array
from ctypes import *

# TODO: What should this be?
#lib = cdll.LoadLibrary('libpysrdada.so')
lib = cdll.LoadLibrary('pysrdada/libpysrdada.so')

class DADA_HANDLE_STRUCT(Structure):
	pass
DADA_HANDLE = POINTER(DADA_HANDLE_STRUCT)

class dada_handle(object):
	DADA_NO_ERROR = 0
	def __init__(self, logname="pysrdada_process"):
		self.lib = lib
		self.obj = DADA_HANDLE()
		
		ret = lib.dada_create(pointer(self.obj), logname)
		if ret != self.DADA_NO_ERROR:
			raise(Exception(self.get_error_string(ret)))
	def __del__(self):
		self.lib.dada_destroy(self.obj)
	def _check_error(self, ret):
		if ret != self.DADA_NO_ERROR:
			raise(Exception(self.get_error_string(ret)))
	def connect(self, key):
		if isinstance(key, basestring):
			key = int(key, 16)
		self._check_error(self.lib.dada_connect(self.obj, key))
	def disconnect(self):
		self._check_error(self.lib.dada_disconnect(self.obj))
	def lock_read(self):
		self._check_error(self.lib.dada_lock_read(self.obj))
	def lock_write(self):
		self._check_error(self.lib.dada_lock_write(self.obj))
	def unlock(self):
		self._check_error(self.lib.dada_unlock(self.obj))
	def read_header(self):
		header = create_string_buffer(self.header_size)
		self._check_error(self.lib.dada_read_header(self.obj,
		                                            pointer(header)))
		return header.value
	def write_header(self, header):
		padded_header = create_string_buffer(self.header_size)
		padded_header[:len(header)] = header
		self._check_error(self.lib.dada_write_header(self.obj,
		                                             pointer(padded_header)))
	def read_buffer(self):
		results = numpy.zeros(self.buffer_size, dtype=numpy.uint8)
		results_ptr = results.ctypes.data_as(POINTER(c_ubyte))
		self._check_error(self.lib.dada_read_buffer(self.obj,
		                                            results_ptr))
		return results
	def write_buffer(self, data):
		data = data.view(dtype=numpy.uint8)
		if len(data) < self.header_size:
			padded = numpy.zeros(self.buffer_size, dtype=numpy.uint8)
			padded[:len(data)] = data
		else:
			padded = data
		padded_ptr = padded.ctypes.data_as(POINTER(c_ubyte))
		self._check_error(self.lib.dada_write_buffer(self.obj,
		                                            padded_ptr))
	def get_error_string(self, error):
		self.lib.dada_get_error_string.restype = c_char_p
		return self.lib.dada_get_error_string(error)
	@property
	def eod(self):
		self.lib.dada_is_eod.restype = c_int
		return bool(lib.dada_is_eod(self.obj))
	@property
	def key(self):
		self.lib.dada_get_key.restype = c_int
		return lib.dada_get_key(self.obj)
	@property
	def header_size(self):
		self.lib.dada_get_header_size.restype = c_uint64
		return lib.dada_get_header_size(self.obj)
	@property
	def buffer_size(self):
		self.lib.dada_get_buffer_size.restype = c_uint64
		return lib.dada_get_buffer_size(self.obj)

if __name__ == "__main__":
	
	ctx = dada_handle("pysrdada_test")
	ctx.connect(0xdada)
	print hex(ctx.key)
	ctx.lock_write()
	ctx.write_header("Hello, world!")
	ctx.write_buffer(numpy.array([1,2,3,4], dtype=numpy.float32))
	ctx.unlock()
	ctx.lock_read()
	print ctx.header_size
	print ctx.buffer_size
	print ctx.read_header()
	while not ctx.eod:
		print ctx.read_buffer().view(dtype=numpy.float32)
	ctx.disconnect()
