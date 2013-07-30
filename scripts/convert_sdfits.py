#!/usr/bin/env python
"""
convert_sdfits.py
-----------------
Convert an LA file of a single antenna into an SD-FITS file. 
Useful for import into CASA/ AOFlagger.

"""

import os, datetime, numpy as np, pyfits as pf, pylab as plt
from lib.sdfits import *


# Number of bytes per n_int integs, integ time, number integs
OFFSET_DELTA, INT_TIME, N_INT = 1044480000, 8.53333,100
(latitude, longitude, elevation) = ('36.8', '-118.2', 1222)


def dt(idx):
    """ Convert timestamp to date and time for SD-FITS """

    tdiff = idx * INT_TIME
    dt = datetime.datetime(2013,06,16,4,53,04) + datetime.timedelta(seconds=tdiff)

    date = dt.strftime("%Y-%m-%d")
    # TODO: Check this is correct
    time = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond * 1e-6
    return (date, time)


if __name__ == '__main__':

    la = np.fromfile('data/full_band.LA', dtype='uint32')
    la = la.reshape(la.shape[0]/2400, 2400)
    
    # Vaguely calibrate it (get it out of 1e9 units!)
    la = la * 1.0 / np.max(la) * 10000
    x = la[::2]
    y = la[1::2]

    print "Creating FITS image"
    hdu = pf.PrimaryHDU(la)
    hdu.header['DATEREF'] = '2013-06-16T04:53:03'
    hdu.header['CTYPE1'] = 'FREQ    '
    hdu.header['CRPIX1'] = 1.0
    hdu.header['CRVAL1'] = 30000000
    hdu.header['CDELT1'] = 24000

    hdu.header['CTYPE1'] = 'UTC'
    hdu.header['CRPIX1'] = 1.0
    hdu.header['CRVAL1'] = 0.0
    hdu.header['CDELT1'] = 8.5333

    hdulist = pf.HDUList([hdu])

    fname = "leda64ov_fullband.fits"
    print "Saving %s"%fname
    if os.path.exists(fname):
        os.remove(fname)
    hdulist.writeto(fname)
    hdulist.close()


    print "Creating SD-FITS"
    hdulist = generateBlankSDFits(x.shape[0], 'lib/header_primaryHDU.txt', 'lib/header_dataHDU.txt',
                                  'lib/coldefs_dataHDU.txt')

    print hdulist.info()

    print "Filling with data"
    hdulist[1].data["EXPOSURE"][:] = INT_TIME
    hdulist[1].data["RESTFRQ"][:] = 30e6
    hdulist[1].data["OBJECT"][:] = "NorthCelPol"
    hdulist[1].data["OBSMODE"][:] = "FIXED"
    hdulist[1].data["BEAM"][:] = 1
    hdulist[1].data["CYCLE"][:] = 1
    hdulist[1].data["IF"][:] = 1
    hdulist[1].data["OBJ-RA"][:] = 0
    hdulist[1].data["OBJ-DEC"][:] = 0
    hdulist[1].data["FREQRES"][:] = 24e3
    hdulist[1].data["BANDWID"][:] = 14.4e6 * 4
    hdulist[1].data["CRPIX1"][:] = 1
    hdulist[1].data["CRVAL1"][:] = 30e6
    hdulist[1].data["CDELT1"][:] = 24e3
    

    for row in range(x.shape[0]):
        hdulist[1].data["DATA"][row] = (x[row], y[row])
        d, t = dt(row)

        hdulist[1].data["SCAN"][:] = row
        hdulist[1].data["DATE-OBS"][row] = d
        hdulist[1].data["TIME"][row] = t

    fname = "leda64ov_fullband.sdfits"
    print "Saving %s"%fname
    if os.path.exists(fname):
        os.remove(fname)
    hdulist.writeto(fname)
    hdulist.close()
