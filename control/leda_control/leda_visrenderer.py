#!/usr/bin/env python

from matplotlib.colors import LogNorm
#from pylab import *
from pylab import figure, subplot, pcolor, title, colorbar, axis, savefig, cm
from numpy import loadtxt
import os
import glob
import subprocess

from generate_vismatrix_plots import generate_vismatrix_plots

"""

visrenderer.py
  Wait for new data
  Generate image files

"""

class LEDAVisMatrixProcess(object):
	def __init__(self, path, outpath):
		# Path to leda_visconverter executable
		self.path = path
		self.outpath = outpath
	def getLatestFile(self, rank=0):
		# TODO: Check that the latest file contains at least one complete
		#         matrix, and otherwise open the 2nd latest.
		return sorted(glob.glob(self.outpath + "/*.dada"),
		              key=os.path.getmtime, reverse=True)[rank]
	def dumpVisMatrixImages(self, stem):
		dadafile = self.getLatestFile()
		print "Gen'ing vismatrix image from", dadafile
		ret = subprocess.call(self.path + " %s %s" % (dadafile,stem),
		                      shell=True)
		if ret != 0:
			print "Failed; trying next oldest file"
			dadafile = self.getLatestFile(rank=1)
			print "Gen'ing vismatrix image from", dadafile
			ret = subprocess.call(self.path + " %s %s" % (dadafile,stem),
			                      shell=True)
			if ret != 0:
				print "Failed again!"
		image_filename = generate_vismatrix_plots(stem)
		return image_filename

# This will continuously regenerate the image every interval
if __name__ == "__main__":
	import sys
	from sys import argv
	import time
	if len(argv) <= 1:
		print "Usage: leda_visrenderer.py datapath filestem interval"
		sys.exit(0)
	datapath = "/data1/one" if len(argv) <= 1 else argv[1]
	stem = "vismatrix" if len(argv) <= 2 else argv[2]
	interval = 30 if len(argv) <= 3 else float(argv[3])
	#exepath  = "/home/leda/leda_control/leda_visconverter"
	exepath  = "./leda_visconverter"
	
	ctx = LEDAVisMatrixProcess(exepath, datapath)
	
	running = True
	while running:
		print "Dumping new images"
		ctx.dumpVisMatrixImages(stem)
		time.sleep(interval)
	print "Exiting"
