#!/usr/bin/env python
""" arx_cal.py -- Auto-calibrate ARX gain levels

Extension of arx.py class for controlling ARX settings, which
adds methods for calibrating gain levels. When run as an executable,
a user-prompted calibration routine is performed.
"""

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"


import subprocess
import time
import numpy as np
import math
import sys
from async import AsyncCaller
import arx

from leda_config import arx_config, roach_config

def get_adc_samples(roach):
    """ Grab ADC values using adc16_dump_chans """
    nstands = 16
    npols   = 2
    nsamps  = 1024
    #return 40 * np.random.standard_normal((nsamps, nstands, npols))
    sp = subprocess.Popen(["adc16_dump_chans.rb", "-l", str(nsamps), roach],
                          stdout=subprocess.PIPE)
    out, err = sp.communicate()
    if len(out) < 1024:
        print "ERROR adc16_dump_chans.rb output:\n---"
        print out
        print "---"
    data = np.fromstring(out, sep=' ', dtype='int')
    try:
        data = data.reshape(nsamps, nstands, npols)
    except ValueError:
        return None
    return data

class ArxCalOVRO(arx.ArxOVRO):
    """ ARX Autocalibration class

    This class extends ArxOVRO with methods for autotuning to find the
    best attenuation settings for consistent ADC power across all inputs.
    """
    def __init__(self, verbose=False):
        super(ArxCalOVRO, self).__init__()
        self.verbose = False

        self.bad_thresh = 4.0
        self.nrepeat    = arx_config.snap_iters
        self.sleeptime  = 1.0
        self.roaches    = roach_config.roach_list

    def _get_nearest_atten(self, val):
        return int(val / 2. + 0.5) * 2

    def _get_residual_atten(self, val):
        return val - self._get_nearest_atten(val)

    def computeCalibration(self, target_rms):
        print "Computing updated ARX calibration"

        async = AsyncCaller()
        stddevs = []
        for t in xrange(self.nrepeat):
            print "  Sampling ADC inputs (rep %i)" % (t+1)
            for roach in self.roaches:
                async(get_adc_samples)(roach)
            roach_samples = async.wait()
            if None in roach_samples:
                raise ValueError("One or more ADC reads failed")
            samples = np.hstack(roach_samples)
            stddevs.append(samples.std(axis=0))
            time.sleep(self.sleeptime)
        stddevs = np.array(stddevs)
        # Note: Shape is (nrepeat,nstands,npols)

        # Compute median of repetitions
        stddevs = np.median(stddevs, axis=0)

        # Find and deal with bad stands and pols
        self.bad_stands  = [0 for ii in range(256)]
        self.semi_stands = [0 for ii in range(256)]
        self.cal_atten   = [0 for ii in range(256)]

        typical = np.median(stddevs) # Median of all inputs
        for i in xrange(stddevs.shape[0]):
            polA_bad = stddevs[i][0] < self.bad_thresh
            polB_bad = stddevs[i][1] < self.bad_thresh
            if polA_bad and polB_bad:
                self.bad_stands[i] = 1
                stddevs[i][0] = stddevs[i][1] = typical
            elif polA_bad:
                self.semi_stands[i] = 1
                stddevs[i][0] = stddevs[i][1]
            elif polB_bad:
                self.semi_stands[i] = 1
                stddevs[i][1] = stddevs[i][0]

        # Average the two pols (as there is no per-pol ARX gain control)
        stddevs = stddevs.mean(axis=1)

        # Update the attenuation values
        for i, x in enumerate(stddevs):
            delta_atten = int(10*math.log10(x / target_rms))
            #self.at2_settings[i+1] += delta_atten
            self.cal_atten[i] = delta_atten

    def applyCalibration(self):
        """ Apply computed calibration to stands"""
        for ii in range(len(self.cal_atten)):
            curr1, curr2, delt = self.at1_settings[ii], self.at2_settings[ii], self.cal_atten[ii]
            if delt > 0:
                if curr2 + delt < 20:
                    self.at2_settings[ii] += delt
                    self.at2_changed[ii] = 1
                elif curr1 + delt < 20:
                    self.at1_settings[ii] += delt
                    self.at1_changed[ii] = 1
                elif curr1 + delt/2 < 20 and curr2 + delt/2 < 20:
                    self.at1_settings[ii] += delt/2
                    self.at2_settings[ii] += delt/2
                    self.at1_changed[ii] = 1
                    self.at2_changed[ii] = 1
            if delt < 0:
                if curr2 + delt > 0:
                    self.at2_settings[ii] += delt
                    self.at2_changed[ii] = 1
                elif curr1 + delt > 0:
                    self.at1_settings[ii] += delt
                    self.at1_changed[ii] = 1
                elif curr1 + delt/2 > 0 and curr2 + delt/2 > 0:
                    self.at1_settings[ii] += delt/2
                    self.at2_settings[ii] += delt/2
                    self.at1_changed[ii] = 1
                    self.at2_changed[ii] = 1

    def listCalibration(self):
        """ List computed calibration values """
        print "Computed attenuation deltas (dB):"
        print self.cal_atten
        print "Bad stands:"
        for ii in range(256):
            if self.bad_stands[ii] == 1:
                print ii+1,
        print ""
        print "Semi-bad stands (one pol out):"
        for ii in range(256):
            if self.semi_stands[ii] == 1:
                print ii+1,

if __name__ == '__main__':

    print "LEDA-OVRO ARX auto-tuner"
    print "------------------------"

    start_config = arx_config.default_config
    target_rms   = arx_config.target_rms
    n_iters      = arx_config.arx_cal_iters

    print "Initial config: %s" % start_config
    print "Target RMS:     %i" % target_rms
    print "No. iterations: %i" % n_iters

    time.sleep(1)

    cal = ArxCalOVRO()
    cal.loadSettings(start_config)

    for ii in range(n_iters):
        print "Iteration %i of %i" % (ii + 1, n_iters)
        cal.computeCalibration(target_rms)
        cal.applyCalibration()
        cal.applySettings()
