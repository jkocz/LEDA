#!/usr/bin/env python
""" Auto-calibrate ARX gain levels """

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import os
from arx_cal import *
from adc16_initall import *

from leda_config import arx_config, roach_config

if __name__ == '__main__':
    
    # ARX Settings
    filename      = arx_config.default_config
    target_rms    = arx_config.default_rms
    n_iter        = arx_config.arx_cal_iters
    reprogram_arx = True
    autocal_arx   = True
    savecal_arx   = True
    disable_bad   = False

    a = ArxCalOVRO()
    a.loadSettings(filename)
    
    if reprogram_arx:
        a.applySettings()
    
    if autocal_arx:
        for ii in range(n_iter): 
            print "Autocal iteration %i of %i"%(ii+1, n_iter)
            try:    
                a.computeCalibration(target_rms)
            except ValueError:
                print "ADC read failed! Retrying..."
                time.sleep(1)
                a.computeCalibration(target_rms)
            
            curr_deltas = a.cal_atten
            for s in a.bad_stands:
                curr_deltas[s-1] = 0
            for s in a.semi_stands:
                curr_deltas[s-1] = 0
                    
            if abs(max(curr_deltas)) < 2:
                print "Optimal settings reached."
                break
                
            a.listCalibration()
            a.applyCalibration()
            a.applySettings(set_fil=False, set_ats=False, set_fee=False)        
    
    print "Final calibration values:"
    try:    
        a.computeCalibration(target_rms)
    except ValueError:
        print "ADC read failed! Retrying..."
        time.sleep(1)
        a.computeCalibration(target_rms)
    a.listCalibration()
    
    if disable_bad:
       a.disableBadStands()
    
    print "Final ARX settings:"
    a.listSettings()
    
    if savecal_arx:
        print "Saving to file..."
        filename_out = 'config/autocalibrated_rms%i_adcgain%ix'%(target_rms, adc_gain) 
        try:
            os.remove(filename_out)
            print "File exists, deleting..."
        except OSError:
            pass
        a.saveSettings(filename_out)
        print "New calibration saved to %s"%filename_out
