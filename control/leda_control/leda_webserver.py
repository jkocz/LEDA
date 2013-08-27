#!/usr/bin/env python

"""

By Ben Barsdell (2013)

On init, call remotevis.open()
When 'start' is clicked, call remotevis.open()
Every 10 secs, call remotevis.update()
  Set last_vis_update = now

On ajax msg "get_vis=visname&i=0&j=1":
  if modified_time(visname+".png") is before last_vis_update:
    imgdata = ledavis.get(msg)
    save imgdata to visname+".png"

key = ""
for 1 to 65536 do
  key = hash(key + password + salt)

TODO: Add email alerts
        Register recipients with desired alerts

"""
"""
import hashlib

def key_stretch(password, salt):
	key = ""
	for i in xrange(65536):
		h = hashlib.sha512()
		h.update(key + password + salt)
		key = h.hexdigest()
	return key
"""	
import os
import sys
import tornado
import tornado.ioloop
import tornado.web
from tornado import websocket
from tornado.options import define, options
from uuid import uuid4
import json
import base64
import time
import datetime
import random
import smtplib
from email.mime.text import MIMEText

from leda_logger import LEDALogger
from leda_remotecontrol import LEDARemoteHeadNodeControl
from leda_remotevis import LEDARemoteHeadNodeVis

def send_email(recipients, frm, subject, msg):
	msg = MIMEText(msg)
	msg['To']      = ', '.join(recipients)
	msg['From']    = frm
	msg['Subject'] = subject
	
	# Send the message via our own SMTP server, but don't include the
	# envelope header.
	s = smtplib.SMTP('localhost')
	s.sendmail(frm, recipients, msg.as_string())
	s.quit()

# Command line options
define("port", default=8888, help="Run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self, remote_host, control_port, vis_port):
		self.remote_host = remote_host
		logstream   = sys.stderr
		debuglevel  = 1
		self.log    = LEDALogger(logstream, debuglevel)
		self.leda   = LEDARemoteHeadNodeControl(self.remote_host,
		                                        control_port,
		                                        self.log)
		self.ledavis = LEDARemoteHeadNodeVis(self.remote_host,
		                                     vis_port,
		                                     self.log)
		self.ledavis.open()
 #self.last_vismatimage_time >= self.min_vismat_refresh_time:
		"""
		self.min_adcimage_refresh_time = 14
		self.min_vismat_refresh_time = 10000#30
		self.last_adcimage_time = 0
		self.last_vismatimage_time = 0
		"""
		self.last_status_time   = 0
		self.min_refresh_time   = 4
		self.last_vis_update_time = 0
		self.min_vis_refresh_time = 10
		self.last_vis_get_time    = 0
		self.min_vis_get_time     = 0.1
		self.viserror_imgdata = open("static/images/viserror.png", 'rb').read()
		
		self.alerts = {'gpu_temp': False,
		               'disk_use': False}
		self.alert_subscribers = {'bbarsdel@gmail.com': ['gpu_temp',
		                                                 'disk_full']}
		# Note: First is rising threshold, second is falling
		self.gpu_temp_thresh = (50, 40)
		self.disk_use_thresh = (90, 80)
		
		self.updateStatus()
		handlers = [
			(r"/", MainHandler),
			(r"/ajax", AJAXHandler),
			(r"/vis", VisHandler),
			]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			xsrf_cookies=True,
			autoescape="xhtml_escape",
			)
		tornado.web.Application.__init__(self, handlers, **settings)
		
	def checkAlerts(self):
		status = self.status['control']
		if 'gpu_info' in status:
			gpu_info = status['gpu_info']
			if 'temp' in gpu_info:
				gpu_temp = float(gpu_info['temp'])
				self.checkAlert('gpu_temp', gpu_temp, self.gpu_temp_thresh)
		if 'disk_info' in status:
			disk_info = status['disk_info']
			if 'percent' in disk_info:
				disk_use = int(disk_info['percent'])
				self.checkAlert('disk_use', disk_use, self.disk_use_thresh)
						
	def checkAlert(self, name, value, thresholds):
		if not self.alerts[name]:
			if value > thresholds[0]:
				self.alerts[name] = True
				self.raiseAlert(name, thresholds[0])
		else:
			if value <= thresholds[1]:
				self.alerts[name] = False
				
	def raiseAlert(self, alert_name, threshold):
		recipients = []
		for subsriber, subscribed_alerts in self.alert_subscribers.items():
			if alert_name in subscribed_alerts:
				recipients += [subscriber]
		utc = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H:%M:%S")
		send_email(recipients, "noreply@ledaovro.lwa.ovro.caltech.edu",
		           "LEDA OVRO alert",
		           "The value of %s exceeded the threshold of %s at UTC %s" \
			           % (alert_name, str(threshold), utc))
	    
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
				# TODO: This needs to be re-done to check for any server/stream
				#         breaking (or all satisfying) the threshold conditions.
				#       Also need to allow simple events (e.g., corr_start)
				#self.checkAlerts()
				
	def updateVis(self):
		print "Vis update request"
		if time.time() - self.last_vis_update_time >= self.min_vis_refresh_time:
			print "Requesting updated vis data from head node"
			self.last_vis_update_time = time.time()
			ret = self.ledavis.update()
			if ret is None:
				print "Vis connection down"
				print "Reconnecting"
				self.ledavis.connect()
	def getVis(self, visname, i, j):
		print "Request for vis '%s' (i=%i j=%i)" % (visname,i,j)
		#if time.time() - self.last_vis_get_time >= self.min_vis_get_time:
		imgdata = self.ledavis.get("%s=1&i=%i&j=%i" % (visname,i,j))
		if imgdata is None:
			print "Vis connection down, cannot get data"
			imgdata = self.viserror_imgdata
		#else:
			#filename = "static/images/latest_vis.png"
			#open(filename, 'wb').write(imgdata)
		return imgdata
	"""
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
	"""
class MainHandler(tornado.web.RequestHandler):
	def get(self):
		# Generate (random) unique identifier
		session = uuid4()
		self.render("leda_index.html",
		            session=session,
		            status=self.application.status)
class VisHandler(tornado.web.RequestHandler):
	def get(self):
		if ( self.get_argument("mode", default=None) is not None and
		     self.get_argument("i", default=None) is not None and
		     self.get_argument("j", default=None) is not None ):
			
			mode = self.get_argument("mode")
			# Note: Web interface uses 1-based indexing
			i = int(self.get_argument("i")) - 1
			j = int(self.get_argument("j")) - 1
			
			# TODO: Work out how to prevent flooding here
			#         Need something like per-session entries in a cache
			imgdata = self.application.getVis(mode, i, j)
			
			self.set_header('Content-Type', 'image/png')
			self.write(imgdata)
		
class AJAXHandler(tornado.web.RequestHandler):
	def get(self):
		if self.get_argument("status", default=None) is not None:
			self.application.updateStatus()
			self.write(self.application.status)
		"""
		image_updated = False
		if self.get_argument("adc_images", default=None) is not None:
			self.application.updateADCImages()
			image_updated = True
		if self.get_argument("vismatrix_images", default=None) is not None:
			self.application.updateVisMatrixImages()
			image_updated = True
		if image_updated:
			self.write("ok")
		"""
		
		if self.get_argument("start", default=None) is not None:
			mode = self.get_argument("mode")
			ra   = self.get_argument("ra")
			dec  = self.get_argument("dec")
			self.application.leda.startObservation(mode, ra, dec)
			# TODO: Make sure this works so quickly after starting
			self.application.ledavis.open()
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
		elif self.get_argument("update_vis", default=None) is not None:
			self.application.updateVis()
			self.write("ok")
		elif self.get_argument("get_vis", default=None) is not None:
			visname = self.get_argument("get_vis")
			# Note: Web interface uses 1-based indexing
			i = int(self.get_argument("i")) - 1
			j = int(self.get_argument("j")) - 1
			# TODO: Work out how to prevent flooding here
			#         Need something like per-session entries in a cache
			imgdata = self.application.getVis(visname, i, j)
			encoded_image = base64.standard_b64encode(imgdata)
			self.write(encoded_image)

if __name__ == "__main__":
	from configtools import *
	
	tornado.options.parse_command_line()
	
	configfile = getenv('LEDA_CONFIG')
	# Dynamically execute config script
	config = {}
	execfile(configfile, config)
	
	app = Application(remote_host=config['headnodehost'],
	                  control_port=6282, vis_port=6283)
	app.listen(options.port)
	print "Listening for connections..."
	tornado.ioloop.IOLoop.instance().start()
