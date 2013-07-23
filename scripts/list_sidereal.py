#!/usr/bin/env python
"""
list_sidereal.py
----------------
list the sidereal times for a directory.

"""

import re, os, sys, calendar, datetime
import ephem
import numpy as np

# Number of bytes per n_int integs, integ time, number integs
OFFSET_DELTA, INT_TIME, N_INT = 1044480000, 8.53333,100 
(latitude, longitude, elevation) = ('36.8', '-118.2', 1222)

def list_sidereal(search_dir):
    """ Print the sidereal times of dada files in a given directory """
    
    ov = ephem.Observer()
    ov.lon = longitude
    ov.lat = latitude
    ov.elev = elevation
    
    filelist = os.listdir(search_dir)
    pat = '(\d+)-(\d+)-(\d+)-(\d\d):(\d\d):(\d\d)_(\d+).(\d+).(dada)$'
    
    lstlist, dadalist = [], []
    for filename in filelist:
        match = re.search(pat, filename)
        if match:
            # Convert re match to integers, apart from file extension
            (y, m, d, hh, mm, ss, offset1, offset2) = [int(m) for m in match.groups()[:-1]]
            tdiff = offset1 / OFFSET_DELTA * INT_TIME * N_INT
            ov.date = datetime.datetime(y,m,d,hh,mm,ss) + datetime.timedelta(seconds=tdiff)
            lstlist.append(ov.sidereal_time())
            dadalist.append(filename)
    return sorted(zip(lstlist, dadalist))

if __name__ == '__main__':
    
    if len(sys.argv) > 1: search_dir = sys.argv[1]
    else: search_dir = './'
    
    sidelist = list_sidereal(search_dir)
    for (s, f) in sidelist: print s, '\t', f