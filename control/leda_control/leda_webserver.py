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
	def __init__(self, remote_host, remote_port):
		self.remote_host = remote_host
		logstream   = sys.stderr
		debuglevel  = 1
		self.log    = LEDALogger(logstream, debuglevel)
		self.leda   = LEDARemoteHeadNodeControl(self.remote_host,
		                                        remote_port,
		                                        self.log)
 #self.last_vismatimage_time >= self.min_vismat_refresh_time:
		self.min_refresh_time   = 4
		self.min_adcimage_refresh_time = 14
		self.min_vismat_refresh_time = 10000#30
		self.last_status_time   = 0
		self.last_adcimage_time = 0
		self.last_vismatimage_time = 0
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
		"""
		if not self.leda.isConnected():
			print "ERROR: Not connected"
			return
		"""
		if time.time() - self.last_status_time >= self.min_refresh_time:
			print "Requesting updated status from head node"
			self.last_status_time = time.time()
			new_status = self.leda.getStatus()
			
			# TODO: Find a better way to deal with connections issues (isConnected/reconnect etc.)
			
			# Handle failed control
			if new_status is None:
				print "Control connection down"
				self.status = {}
				# TODO: Set all status entries to 'error'
				self.status['roach'] = []
				#self.status['roach'] = [{'flow': 'ok'}]
				self.status['control'] = []
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
		if not self.leda.isConnected():
			print "ERROR: Not connected"
			return
		if time.time() - self.last_adcimage_time >= self.min_adcimage_refresh_time:
			self.last_adcimage_time = time.time()
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
	
	# ***************
	# TODO: Use above func as a base to implement updateVisMatrixImages!
	def updateVisMatrixImages(self):
		print "Visibility matrix update request"
		if not self.leda.isConnected():
			print "ERROR: Not connected"
			return
		if time.time() - self.last_vismatimage_time >= self.min_vismat_refresh_time:
			self.last_vismatimage_time = time.time()
			print "Requesting updated visibility matrix images from head node"
			images = self.leda.getVisMatrixImages()
			if images is None:
				print "Request FAILED"
			else:
				for stream, stream_image in enumerate(images):
					filename = "static/images/vismatrix_svr02_str%02i.png"%(stream+1)
					open(filename, 'wb').write(stream_image)

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
		
		image_updated = False
		if self.get_argument("adc_images", default=None) is not None:
			self.application.updateADCImages()
			image_updated = True
		if self.get_argument("vismatrix_images", default=None) is not None:
			self.application.updateVisMatrixImages()
			image_updated = True
		if image_updated:
			self.write("ok")
		
		if self.get_argument("start", default=None) is not None:
			self.application.leda.startObservation()
		elif self.get_argument("stop", default=None) is not None:
			self.application.leda.stopObservation()
		elif self.get_argument("kill", default=None) is not None:
			self.application.leda.killObservation()
		elif self.get_argument("program_roaches", default=None) is not None:
			self.application.leda.programRoaches()
		elif self.get_argument("create_buffers", default=None) is not None:
			self.application.leda.createBuffers()
		elif self.get_argument("total_power", default=None) is not None:
			ncycles = int(self.get_argument("total_power"))
			self.application.leda.setTotalPowerRecording(ncycles)

if __name__ == "__main__":
	from configtools import *
	
	tornado.options.parse_command_line()
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	config = {}
	execfile(configfile, config)
	
	app = Application(remote_host=config['headnodehost'], remote_port=6282)
	app.listen(options.port)
	print "Listening for connections..."
	tornado.ioloop.IOLoop.instance().start()
