#!/usr/bin/env python

import os
import sys
import tornado
import tornado.ioloop
import tornado.web
from tornado import websocket
from tornado.options import define, options
from uuid import uuid4
import json
import time

import random

from leda_remotecontrol import LEDARemoteHeadNodeControl, LEDALogger

# Command line options
define("port", default=8888, help="Run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		remote_port = 6282
		self.remote_host = "ledagpu4"
		logstream   = sys.stderr
		debuglevel  = 1
		self.log    = LEDALogger(logstream, debuglevel)
		self.leda   = LEDARemoteHeadNodeControl(self.remote_host,
		                                        remote_port,
		                                        self.log)
		self.min_refresh_time   = 4
		self.last_status_time   = 0
		self.last_adcimage_time = 0
		self.updateStatus()
		handlers = [
			(r"/", MainHandler),
			(r"/ajax", AJAXHandler)
			]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			xsrf_cookies=True,
			autoescape="xhtml_escape",
			)
		tornado.web.Application.__init__(self, handlers, **settings)
	    
	def updateStatus(self):
		print "Status request"
		if time.time() - self.last_status_time >= self.min_refresh_time:
			print "Requesting updated status from head node"
			self.last_status_time = time.time()
			new_status = self.leda.getStatus()
			
			# TODO: Find a better way to deal with connections issues (isConnected/reconnect etc.)
			
			# Handle failed control
			if new_status is None:
				print "Control connection down"
				# TODO: Set all other status entries to 'error'
				self.status['headnode'] = {'host':self.remote_host,
										   'alive':'ok',
										   'control':'down'}
				# Try to reconnect
				print "Reconnecting"
				self.leda.connect()
			else:
				self.status = new_status
				self.status['headnode'] = {'host':self.remote_host,
										   'alive':'ok',
										   'control':'ok'}
	def updateADCImages(self):
		print "ADC image update request"
		if time.time() - self.last_adcimage_time >= self.min_refresh_time:
			print "Requesting updated ADC images from head node"
			images = self.leda.getADCImages()
			if images is None:
				print "Request FAILED"
				# TODO: What else here?
			else:
				#print "Received %i images" % len(images)
				# Write images to disk
				for r,roach in enumerate(images):
					for a,adc_image in enumerate(roach):
						filename = "static/images/roach%02i_adc%02i.png"%(r+1,a+1)
						open(filename, 'wb').write(adc_image)
				#for i,image in enumerate(images):
					#image.save("adc_plot_%02i.png"%(i+1), format="png")
					#open("static/images/adc_plot_%02i.png"%(i+1), 'wb').write(image)

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		# Generate (random) unique identifier
		session = uuid4()
		self.render("leda_index.html",
		            session=session,
		            status=self.application.status)
class AJAXHandler(tornado.web.RequestHandler):
	def get(self):
		if self.get_argument("status", default=None) is not None:
			self.application.updateStatus()
			self.write(self.application.status)
		if self.get_argument("adc_images", default=None) is not None:
			self.application.updateADCImages()
			self.write("ok")
		if self.get_argument("start", default=None) is not None:
			self.application.leda.startObservation()
		elif self.get_argument("stop", default=None) is not None:
			self.application.leda.stopObservation()
		elif self.get_argument("kill", default=None) is not None:
			self.application.leda.killObservation()

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = Application()
	app.listen(options.port)
	print "Listening for connections..."
	tornado.ioloop.IOLoop.instance().start()
