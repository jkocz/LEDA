#!/usr/bin/env python

"""
Simple weather sampling script designed for logging
Prints a single line containing a timestamp and a series of tab-separated values

E.g., 2014-11-19T02:30:02     41960.604190    13.30   -17.80  1022.5  190.0   4.0     18.0

Note: Weather station and lat/lon are currently hard-coded for OVRO
"""

import datetime
import ephem # For Julian date
import weather
from urllib2 import HTTPError

if __name__ == "__main__":
    #import sys
    
    station = "KBIH" # Note: Bishop regional; closest to OVRO
    lon = -118.281667
    lat =   37.239777
    
    nattempts = 3
    gnd = None
    for attempt in xrange(nattempts):
        try:
            gnd = weather.GroundWeather(station)
        except HTTPError:
            continue
        else:
            break
    if gnd is None:
        sys.exit(-1)
    
    tec = None
    for attempt in xrange(nattempts):
        try:
            tec = weather.TotalElectronContent()
        except HTTPError:
            continue
        else:
            break
    if tec is None:
        sys.exit(-1)
    """
    print '#' + '\t'.join(['UTC',
                           'DUBLIN_JD',
                           'TEMP_C',
                           'DEWPOINT_C',
                           'PRESSURE_MB',
                           'WIND_DIR_DEGS',
                           'WIND_SPD_KT',
                           'TEC_TECU'])
    """
    utc = datetime.datetime.utcnow()
    utc_str = utc.strftime("%Y-%m-%dT%H:%M:%S")
    # Note: The (Dublin) Julian date is included just for convenience, e.g.,
    #         when plotting.
    dublin_jd = float(ephem.Date(utc))
    print '\t'.join([utc_str,
                     '%.6f' % dublin_jd,
                     '%.2f' % gnd.temp_c,
                     '%.2f' % gnd.dewpoint_c,
                     '%.1f' % gnd.pressure_mb,
                     '%.1f' % gnd.wind_dir_degs,
                     '%.1f' % gnd.wind_speed_kt,
                     '%.1f' % tec.tecmap(lon,lat)])
    
