#!/usr/bin/env python

from matplotlib.colors import LogNorm
#from pylab import *
from pylab import figure, subplot, pcolor, title, colorbar, axis, savefig, cm
from numpy import loadtxt

def generate_vismatrix_plots(stem):
	data_xx_amp   = loadtxt(stem + "_xx.amp")
	data_xx_phase = loadtxt(stem + "_xx.phase")
	data_yy_amp   = loadtxt(stem + "_yy.amp")
	data_yy_phase = loadtxt(stem + "_yy.phase")
	
	figure(figsize=(8,6), dpi=96)
	
	subplot(2,2,1)
	pcolor(data_xx_amp, norm=LogNorm(vmin=1e0, vmax=1e6), cmap=cm.Blues)
	title("Amplitude XX")
	colorbar()
	axis([0,32,0,32])
	
	subplot(2,2,2)
	pcolor(data_xx_phase, vmin=-3.14159, vmax=3.14159, cmap=cm.RdBu)
	title("Phase XX")
	colorbar()
	axis([0,32,0,32])
	
	subplot(2,2,3)
	pcolor(data_yy_amp, norm=LogNorm(vmin=1e0, vmax=1e6), cmap=cm.Blues)
	title("Amplitude YY")
	colorbar()
	axis([0,32,0,32])
	
	subplot(2,2,4)
	pcolor(data_yy_phase, vmin=-3.14159, vmax=3.14159, cmap=cm.RdBu)
	title("Phase YY")
	colorbar()
	axis([0,32,0,32])
	
	outfilename = stem + '.png'
	savefig(outfilename, bbox_inches='tight', pad_inches=0.1)
	
	return outfilename

if __name__ == "__main__":
	from sys import argv
	stem = "vismatrix" if len(argv) <= 1 else argv[1]
	generate_vismatrix_plots(stem)
