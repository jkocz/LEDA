#!/usr/bin/env python

"""
Direct wrapper for common PSRDADA library functions
By Ben Barsdell (2013)
Note: This is very incomplete; only minimal required functionality was wrapped

TODO: Add high-level convenience functions such as:
        Header parsing/formatting
        Numpy interoperation
        More convenient HDU inteface?
          E.g., read/write_header, returning/accepting header dicts
"""

#import numpy
#import array
from ctypes import *
#import warnings
#import sys

try:
	import numpy
except ImportError:
	pass

# Note: Build psrdada with ./configure --enable-shared
_dada = cdll.LoadLibrary('libpsrdada.so')
# TODO: This is only needed for fdopen, used as a way to get FILE* from fileno
_libc = cdll.LoadLibrary('libc.so.6')

key_t = c_uint

def _module_loaded(module):
	# TODO: Nicer way to do this?
	try:
		module
	except NameError:
		return False
	else:
		return True

def bind_thread_to_core(core):
	_dada.dada_bind_thread_to_core.restype = c_int
	err = _dada.dada_bind_thread_to_core(core)
	if err:
		raise Exception("Failed to bind thread to core %i" % core)

def _cast_to_type(string):
	try: return int(string)
	except ValueError: pass
	try: return float(string)
	except ValueError: pass
	return string
def parse_header(headerstr, cast_types=True):
	header = {}
	for line in headerstr.split('\n'):
		try:
			key, value = line.split()
		except ValueError:
			break
		key = key.strip()
		value = value.strip()
		if cast_types:
			value = _cast_to_type(value)
		header[key] = value
	return header
def serialize_header(headerdict, keypadding=32):
	return '\n'.join([str(key).ljust(keypadding-1)+" "+str(val) \
		                  for (key,val) in headerdict.items()]) + '\n'

class multilog_t(Structure):
	pass
class MultiLogObj(object):
	# Note: These come from sys/syslog.h
	LOG_EMERG   = 0	# system is unusable
	LOG_ALERT   = 1	# action must be taken immediately
	LOG_CRIT    = 2	# critical conditions
	LOG_ERR     = 3	# error conditions
	LOG_WARNING = 4	# warning conditions
	LOG_NOTICE  = 5	# normal but significant condition
	LOG_INFO    = 6	# informational
	LOG_DEBUG   = 7	# debug-level messages
	def __init__(self, obj=POINTER(multilog_t)()):
		self.obj = obj
		# Note: Added functionality
		self.verbosity = self.LOG_NOTICE
	def add(self, fileobj):#=sys.stderr.fileno()):
		fn = fileobj.fileno()
		_libc.fdopen.restype = c_void_p
		fp = _libc.fdopen(fn, "w")
		err = _dada.multilog_add(self.obj, fp)
		if err:
			raise Exception("MultiLog: Failed to add file pointer")
	def __call__(self, msg, priority):
		if priority > self.verbosity: # Note: Added functionality
			return
		if not isinstance(msg, basestring):
			msg = str(msg)
		msg += "\n" # Note: Convenient, and important to force flush
		err = _dada.multilog(self.obj, c_int(priority), r"%s", msg)
		if err:
			raise Exception("MultiLog: Failed to write message '%s'" % msg)
	def error(self, msg):
		return self.__call__(msg, self.LOG_ERR)
	def warning(self, msg):
		return self.__call__(msg, self.LOG_WARNING)
	def notice(self, msg):
		return self.__call__(msg, self.LOG_NOTICE)
	def info(self, msg):
		return self.__call__(msg, self.LOG_INFO)
	def debug(self, msg):
		return self.__call__(msg, self.LOG_DEBUG)
class MultiLog(MultiLogObj):
	def __init__(self, name):
		MultiLogObj.__init__(self)
		self._dada = _dada # Must keep reference; needed in __del__
		self.obj = _dada.multilog_open(name, 0)
	def __del__(self):
		self._dada.multilog_close(self.obj)

class ipcbuf_t(Structure):
	pass
class IPCBufObj(object):
	def __init__(self, obj=POINTER(ipcbuf_t)()):
		self.obj = obj
	@property
	def bufsz(self):
		if not self.obj:
			raise Exception("IPCBuf: Object is NULL (is HDU connected?)")
		_dada.ipcbuf_get_bufsz.restype = c_uint64
		return _dada.ipcbuf_get_bufsz(self.obj)
	@property
	def nbufs(self):
		if not self.obj:
			raise Exception("IPCBuf: Object is NULL (is HDU connected?)")
		_dada.ipcbuf_get_nbufs.restype = c_uint64
		return _dada.ipcbuf_get_nbufs(self.obj)
	@property
	def eod(self):
		if not self.obj:
			raise Exception("IPCBuf: Object is NULL (is HDU connected?)")
		return bool(_dada.ipcbuf_eod(self.obj))
	def get_next_read(self):
		_dada.ipcbuf_get_next_read.restype = c_void_p#c_char_p
		header_size = c_uint64()
		ptr = _dada.ipcbuf_get_next_read(self.obj,
		                                 addressof(header_size))
		header_size = header_size.value
		return ptr, header_size
	def mark_cleared(self):
		err = _dada.ipcbuf_mark_cleared(self.obj)
		if err:
			raise Exception("IPCBuf: Failed to mark as cleared")
	def get_next_write(self):
		_dada.ipcbuf_get_next_write.restype = c_void_p#c_char_p
		ptr = _dada.ipcbuf_get_next_write(self.obj)
		return ptr
	def mark_filled(self, nbytes):
		err = _dada.ipcbuf_mark_filled(self.obj, c_uint64(nbytes))
		if err:
			raise Exception("IPCBuf: Failed to mark as filled")
	# ...
	# -----------------------------
	# New convenience methods below
	# -----------------------------
	def view(self):
		ptr, nbytes = self.get_next_read()
		buf = create_string_buffer(nbytes)
		memmove(buf, ptr, nbytes)
		return buf.value
	def read(self):#, buf=None):
		#ptr, nbytes = self.get_next_read()
		##if buf is None:
		#buf = create_string_buffer(nbytes)
		##else:
		##	if len(buf) < nbytes:
		##		raise Exception("IPCBuf: Given buffer is too small")
		#memmove(buf, ptr, nbytes)
		result = self.view()
		self.mark_cleared()
		##return buf
		#return buf.value
		return result
	def write(self, buf):
		if isinstance(buf, basestring):
			# Note: Buffer length is string length + 1 for null terminator
			buf = create_string_buffer(buf)
		nbytes = len(buf)
		ptr = self.get_next_write()
		memmove(ptr, buf, nbytes)
		self.mark_filled(nbytes)

# TODO: This needs to create/allocate a ipcbuf_t struct instance, set
#         it to ipcbuf_init, and then either create/destroy or connect/disconnect
"""
class IPCBuf(IPCBufObj):
	def __init__(self, key=0xdada, nbufs=4, bufsz=524288, num_readers=1):
		IPCBufObj.__init__(self)
		err = _dada.ipcbuf_create(self.obj, key_t(key),
		                          c_uint64(nbufs),
		                          c_uint64(bufsz),
		                          c_uint(num_readers))
		if err:
			raise Exception("IPCBuf: Failed to create buffer")
	def __del__(self):
		_dada.ipcbuf_destroy(self.obj)
"""

class ipcio_t(Structure):
	pass
class IPCIoObj(IPCBufObj):
	def __init__(self, obj=POINTER(ipcio_t)()):
		self.obj = obj
	def read(self, buf, nbytes=None):
		if _module_loaded(numpy):
			if isinstance(buf, numpy.ndarray):
				nbytes = buf.nbytes
				#buf    = buf.ctypes.data # Doesn't work
				buf    = buf.ctypes.data_as(c_void_p)
		if nbytes is None:
			nbytes = len(buf)
		_dada.ipcio_read.restype = c_ssize_t
		ret = _dada.ipcio_read(self.obj, buf, c_size_t(nbytes))
		if ret < 0:
			raise Exception("IPCIo: Failed to read")
		return ret
	def write(self, buf, nbytes=None):
		_dada.ipcio_read.restype = c_ssize_t
		if isinstance(buf, basestring):
			# Note: Buffer length is string length + 1 for null terminator
			buf = create_string_buffer(buf)
		elif _module_loaded(numpy):
			if isinstance(buf, numpy.ndarray):
				nbytes = buf.nbytes
				buf    = buf.ctypes.data
		if nbytes is None:
			nbytes = len(buf)
		ret = _dada.ipcio_write(self.obj, buf, c_size_t(nbytes))
		if ret < 0:
			raise Exception("IPCIo: Failed to write")
		return ret
	# ...

class dada_hdu_t(Structure):
	pass
dada_hdu_t._fields_ = [("log",              POINTER(multilog_t)),
                       ("data_block",       POINTER(ipcio_t)),
                       ("header_block",     POINTER(ipcbuf_t)),
                       ("header",           c_char_p),
                       ("header_size",      c_uint64),
                       ("data_block_key",   key_t),
                       ("header_block_key", key_t)]
class DadaHDUObj(object):
	def __init__(self, obj=POINTER(dada_hdu_t)()):
		self.obj = obj
	@property
	def log(self):
		return MultiLogObj(self.obj.contents.log)
	@property
	def data_block(self):
		return IPCIoObj(self.obj.contents.data_block)
	@property
	def header_block(self):
		return IPCBufObj(self.obj.contents.header_block)
	@property
	def header(self):
		return self.obj.contents.header
	@property
	def header_size(self):
		return self.obj.contents.header_size
	@property
	def data_block_key(self):
		return int(self.obj.contents.data_block_key)
	@property
	def header_block_key(self):
		return int(self.obj.contents.header_block_key)
	def set_key(self, key):
		# Allow setting via string representation of hex
		if isinstance(key, basestring):
			key = int(key, 16)
		_dada.dada_hdu_set_key(self.obj, key)
	def connect(self):
		err = _dada.dada_hdu_connect(self.obj)
		if err:
			raise Exception("Failed to connect")
	def disconnect(self):
		err = _dada.dada_hdu_disconnect(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to disconnect")
	def lock_read(self):
		err = _dada.dada_hdu_lock_read(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to lock for reading")
	def unlock_read(self):
		err = _dada.dada_hdu_unlock_read(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to unlock from reading")
	def lock_write(self):
		err = _dada.dada_hdu_lock_write(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to lock for writing")
	#def lock_write_spec(self, writemode):
	def unlock_write(self):
		# Note: This also sets eod on the data stream
		err = _dada.dada_hdu_unlock_write(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to unlock from writing")
	def open_view(self):
		err = _dada.dada_hdu_open_view(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to open for viewing")
	def close_view(self):
		# TODO: Bug in this function? Always produces "invalid ipcio_t".
		#         Is closing not necessary when viewing?
		err = _dada.dada_hdu_close_view(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to close from viewing")
	def open(self):
		err = _dada.dada_hdu_open(self.obj)
		if err:
			raise Exception("DadaHDU: Failed to open")
class DadaHDU(DadaHDUObj):
	"""This class automatically manages creation/destruction of a
	dada_hdu instance.
	"""
	def __init__(self, log):
		DadaHDUObj.__init__(self)
		self._dada = _dada # Must keep reference; needed in __del__
		self._log = log # Must keep reference
		_dada.dada_hdu_create.restype = POINTER(dada_hdu_t)
		self.obj = _dada.dada_hdu_create(log.obj)
	def __del__(self):
		self._dada.dada_hdu_destroy(self.obj)
		self.obj = 0

if __name__ == "__main__":
	
	#ipcbuf = IPCBuf(key=0xaada) # Not implemented yet
	
	print "Binding thread to core 0"
	bind_thread_to_core(0)
	
	print "Creating MultiLog"
	log = MultiLog("pysrdada2")
	print "Creating HDU"
	hdu = DadaHDU(log)
	print "Setting key"
	hdu.set_key(0xdada)
	hdu.set_key("dada")
	print "Key:", hex(hdu.data_block_key)
	
	print "Connecting"
	hdu.connect()
	print "Header buffer size:", hdu.header_block.bufsz
	print "Data buffer size:  ", hdu.data_block.bufsz
	
	print "Locking for write"
	hdu.lock_write()
	print "Writing header"
	hdu.header_block.write("MY_KEY       MY_VAL100\n")
	
	print "Writing data"
	hdu.data_block.write("Hello my old friend")
	
	print "Unlocking write"
	hdu.unlock_write()
	print "Locking for read"
	hdu.lock_read()
	#hdu.open_view()
	
	#print hdu.header_block.read()
	#print hdu.header_block.view()
	
	#hdu.unlock_read()
	#hdu.close_view()
	
	print "Opening"
	hdu.open()
	print "Printing header"
	print hdu.header
	
		
	import numpy as np
	data = np.ones(10, dtype=np.uint8)
	hdu.data_block.read(data)
	#hdu.data_block.read(data.data)
	#hdu.data_block.read(data.ctypes.data, len(data))
	print data
	
	print "Reading data"
	buf = create_string_buffer(hdu.data_block.bufsz)
	while hdu.data_block.read(buf):
		print buf.value
	
	
	print "Done"
	
