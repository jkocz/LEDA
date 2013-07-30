#!/usr/bin/env python
"""
lilo_and_stitch.py
------------------
Get multiple L-files and stitch them together.

"""


import re, os, sys, calendar, datetime, numpy as np, pyfits as pf

import pylab as plt



if __name__ == '__main__':

    
    #filePairer(in_dir)
    
    # First data taken has issue with timestamps (25 vs 26 cycles)
    filenames = [
      'data/band1_045304_0.LA',
      'data/band2_045304_0.LA',
      'data/band3_045304_0.LA',
      'data/band4_045304_0.LA'
      ]
    
    print "Combining LAs..."
    la_list = [np.fromfile(f, dtype='float32') for f in filenames]
    la_len = la_list[0].shape[0]
    la_list = [la.reshape(la_len/600,600) for la in la_list]

    print "Stitching..."
    la = np.concatenate(la_list, axis=1)
    plt.plot(np.abs(la[0,0:2400]))
    plt.show()
    
    print "Dumping to file..."
    la.tofile('full_band.LA')

    print "OK"
    