
import threading, Queue

class AsyncCaller(object):
	def __init__(self):
		self.ncalls = 0
		self.queue = Queue.Queue()
	def __call__(self, func):
		"""Returns an asynchronous version of a function
		"""
		self.ncalls += 1
		target = lambda *args, **kwargs: self.queue.put(func(*args, **kwargs))
		def foo(*args, **kwargs):
			t = threading.Thread(target=target, args=args, kwargs=kwargs)
			t.daemon = True
			t.start()
		return foo
	def wait(self, ncalls=-1, callback=None):
		"""Waits for calls to complete and returns list of return values.
		   ncalls can be used to limit the number of calls to wait for.
		   callback is (optionally) called with the return value of each call.
		   If callback returns False, no further calls will be waited on.
		"""
		if ncalls == -1:
			ncalls = self.ncalls
		elif ncalls > self.ncalls:
			raise IndexError("Cannot wait for %i call(s); only %i were/was made" \
				                 % (ncalls, self.ncalls))
		return_vals = []
		for _ in xrange(ncalls):
			return_vals.append(self.queue.get())
			self.ncalls -= 1
			if callback is not None:
				cbret = callback(return_vals[-1])
				if cbret is not None and cbret == False:
					break
		return return_vals
