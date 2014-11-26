#!/usr/bin/env python
"""
run_outriggers.py - Capture outrigger switching spectra

April 2014 script for catching outrigger spectra in three switching states.
This script manually controls the switching, and assumes a particular antenna
mapping on the ARX card. This mapping will likely be wrong after Lincoln's visit
in May.

"""

import os, sys, time
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('PDF')
import pylab as plt
import hickle as hkl

#sys.path.append('/home/leda/dan/tpspec')
sys.path.append('/home/leda/leda_dev/control/sax_control')

import sax
#from run_spectrometer import *
from ledaspec import *
from prog_all_spectrometer import *

cc = [
    '#1a194f', '#0b566c', '#254094', '#3ab6e4', '#056538',
    '#4ab348', '#90d28f', '#b81f27', '#e77076', '#fa9f3a', '#f1cf11'
    ]

def db(d):
    return 10*np.log10(d)

def snap_outriggers(r16):
    """ Snap all outrigger spectra off rofl15 and rofl16

    Returns a python dictionary with outrigger spectra
    """
    outrigs = {}

    r16.primeSnap()
    r16.wait_for_acc()
    r16.primeSnap()
    r16.wait_for_acc()
    xx, yy = r16.snapUnpack()

    outrigs["252A"] = xx[0]
    outrigs["254A"] = xx[2]
    outrigs["255A"] = xx[4]
    outrigs["256A"] = xx[6]

    outrigs["252B"] = yy[1]
    outrigs["254B"] = yy[3]
    outrigs["255B"] = yy[5]
    outrigs["256B"] = yy[7]

    return outrigs

def plot_outriggers(fmin=0, fmax=100, pmin=40, pmax=100):
        """ Plot outrigger antennas

        fmin: min freq (MHz), default 0
        fmax: max freq (MHz), default 100
        pmin: y-axis power min (default 40)
        pmax: y-axis power max (default 100)

        """
        try:
            f = np.linspace(0,196.608/2, 4096)
            print "Connecting to SAX..."
            s = sax.SaxController()
            print "OK."

            print "Connecting to FPGA...",
            r16 = Ledaspec('rofl16')
            time.sleep(1)
            r16.fpga.write_int('acc_len', 10000)
            r16.fpga.write_int('ant_sel1', 8)
            r16.fpga.write_int('ant_sel2', 9)
            r16.fpga.write_int('ant_sel3', 10)
            r16.fpga.write_int('ant_sel4', 11)
            r16.fpga.write_int('ant_sel5', 12)
            r16.fpga.write_int('ant_sel6', 13)
            r16.fpga.write_int('ant_sel7', 14)
            r16.fpga.write_int('ant_sel8', 15)
            r16.fpga.write_int('fft_shift', -1)
            r16.fpga.write_int('rst', 0)
            r16.fpga.write_int('rst', 1)
            r16.fpga.write_int('rst', 0)
            time.sleep(1)
            print "OK."

            now = datetime.now()
            ts  = now.strftime("%Y-%m-%d_%HH%MM%SS")

            s.hold_sky()
            sps = snap_outriggers(r16)

            s.hold_cold()
            spc = snap_outriggers(r16)

            s.hold_hot()
            sph = snap_outriggers(r16)

            #tsky = (sps-spc)/(sph-spc)

            outrigs = {
              'sky' : sps,
              'load' : spc,
              'diode' : sph
               }

            s.close()
            now = datetime.now()
            hkl_str = now.strftime("outrigger_report-%Y-%m-%d_%H-%M-%S.hkl")
            outrig_dir = config.outrigger_report_dir
            hkl.dump(outrigs, os.path.join(outrig_dir, hkl_str))


            ii = 0

            plt.figure(figsize=(14,20))
            for antid in ['252A','252B','254A','254B','255A','255B','256A','256B']:
                ii += 1
                plt.subplot(4, 2, ii)
                plt.plot(f, db(sps[antid]), c=cc[6], label="%s S"%antid)
                plt.plot(f, db(spc[antid]), c=cc[1], label="%s D"%antid)
                plt.plot(f, db(sph[antid]), c=cc[3], label="%s L"%antid)
                plt.xlim(fmin, fmax)
                plt.ylim(pmin, pmax)
                plt.title(antid)
                plt.minorticks_on()
                plt.legend(frameon=False)
            #plt.show()
            pdf_str = now.strftime("outrigger_report-%Y-%m-%d_%H-%M-%S.pdf")
            plt.savefig(os.path.join(outrig_dir, "outrigger_report.pdf"))
            plt.savefig(os.path.join(outrig_dir, pdf_str))
        except:
            s.close()
            print "ERROR: Could not plot"
            raise

if __name__ == '__main__':
    plot_outriggers()
