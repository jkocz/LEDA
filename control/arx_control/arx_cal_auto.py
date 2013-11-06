#!/usr/bin/env python
""" Auto-calibrate ARX gain levels """

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

import os
from arx_cal import *
from adc16_initall import *

if __name__ == '__main__':
    
    # ARX Settings
    filename      = 'config/config_15db_15db_on'
    target_rms    = 50
    n_iter        = 5
    reprogram_arx = True
    autocal_arx   = True
    savecal_arx   = True
    
    # ROACH settings
    boffile         = 'l512_actual.bof'
    adc_gain        = 4
    reprogram_fpga  = False
    
    # Main calibration routine
    if reprogram_fpga:
        progdev_all(boffile, adc_gain)
    
    a = ArxCalOVRO()
    a.loadSettings(filename)
    
    if reprogram_arx:
        a.applySettings()
    
    if autocal_arx:
        for ii in range(n_iter): 
            print "Autocal iteration %i of %i"%(ii, n_iter)
            try:    
                a.computeCalibration(target_rms)
            except ValueError:
                print "ADC read failed! Retrying..."
                time.sleep(1)
                a.computeCalibration(target_rms)
            
            if abs(max(a.cal_atten)) < 2:
                print "Optimal settings reached."
                break
                
            a.listCalibration()
            a.applyCalibration()
            a.applySettings(set_fil=False)        
    
    print "Final calibration values:"
    try:    
        a.computeCalibration(target_rms)
    except ValueError:
        print "ADC read failed! Retrying..."
        time.sleep(1)
        a.computeCalibration(target_rms)
    a.listCalibration()
    
    if savecal_arx:
        filename_out = 'config/autocalibrated_rms%i_adcgain%ix'%(target_rms, adc_gain) 
        try:
            os.remove(filename_out)
            print "File exists, deleting..."
        except OSError:
            pass
        a.saveSettings(filename_out)
        print "New calibration saved to %s"%filename_out