
import threading, Queue

class AsyncCaller(object):
	def __init__(self):
		self.ncalls = 0
		self.queue = Queue.Queue()
	def __call__(self, func):
		"""Returns an asynchronous version of a function
		"""
		idx = self.ncalls
		self.ncalls += 1
		target = lambda *args, **kwargs: \
		    self.queue.put((idx,func(*args, **kwargs)))
		def foo(*args, **kwargs):
			t = threading.Thread(target=target, args=args, kwargs=kwargs)
			t.daemon = True
			t.start()
		return foo
	def wait(self, callback=None):
		"""Waits for calls to complete and returns list of return values in the order
		     the calls were made.
		   callback is (optionally) called with the index and return value of each call.
		   If callback returns False, no further calls will be waited on.
		"""
		return_vals = self.wait_n(callback=callback)
		# Sort by call index
		return_vals.sort(key=lambda x: x[0])
		# Return values only
		return [x[1] for x in return_vals]
	
	def wait_n(self, ncalls=-1, callback=None):
		"""Waits for calls to complete and returns a list of (idx,returnval) tuples
		     in the order of completion.
		   ncalls can be used to limit the number of calls to wait for.
		   callback is (optionally) called with the index and return value of each call.
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
				cbret = callback(return_vals[-1][0], return_vals[-1][1])
				if cbret is not None and cbret == False:
					break
		return return_vals
