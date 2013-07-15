
import sys
import datetime

class LEDALogger(object):
	def __init__(self, streams=sys.stderr, debuglevel=1):
		try:
			streams.write("")
		except:
			self.streams = streams
		else:
			self.streams = [streams]
		self.debuglevel = debuglevel
	def copy(self):
		return LEDALogger(self.streams, self.debuglevel)
	def curTime(self):
		now = datetime.datetime.today()
		now_str = now.strftime("%Y-%m-%d-%H:%M:%S.%f")
		return now_str
	def write(self, message, level=1):
		output = "[" + self.curTime() + "]"
		if level == -1:
			output += " WARN"
		elif level == -2:
			output += " ERR"
		output += " " + message.replace("`","'") + "\n"
		for stream in self.streams:
			stream.write(output)
