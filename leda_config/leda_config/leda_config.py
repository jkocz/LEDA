#! /usr/bin/env python
# encoding: utf-8
"""
leda_config.py
==============

This files stores configuration parameters and global variables that are required across
the LEDA project. 
"""

import os
import ephem


SPEED_OF_LIGHT = 299792458

########
# PSR-DADA Settings
########

OFFSET_DELTA     = 115187712   # Bytes per dada file 
INT_TIME         = 8.33333     # Integration time (s)
N_INT_PER_FILE   = 10          # Number integrations (?)

########
# Station location - OVRO
########

(latitude, longitude, elevation) = ('37.240391', '-118.2', 1184)

ovro      = ephem.Observer()
ovro.lon  = longitude
ovro.lat  = latitude
ovro.elev = elevation

########
# LedaFits defaults
#######
CH_WIDTH          = 24e3
SUB_BW            = 2.616e6
TELESCOP          = "LWA-OVRO"
ARRNAM            = "LEDA-512"

# Default files to load to fill in FITS-IDI
fileroot = os.path.abspath(os.path.dirname(__file__))

# A few sources to phase to
src_names = ['CYG', 'CAS', 'TAU', 'VIR']
src_ras   = [299.86791, 350.84583, 83.63333, 187.705833]
src_decs  = [40.733888, 58.810833, 22.01444, 12.39111]

