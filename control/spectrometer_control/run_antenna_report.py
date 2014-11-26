#!/usr/bin/env python
"""
run_antenna_report.py
---------------------

Run an antenna report and save output to file. This gets a bandpass
for all 512 signal paths, and saves it to a hickle file.
"""

import os
from datetime import datetime
from prog_all_spectrometer import *
import hickle as hkl
import shutil

import matplotlib
matplotlib.use('Agg', warn=False)
import pylab as plt
from matplotlib.backends.backend_pdf import PdfPages


def ant_report(sp, fpath):
    """ Generate antenna report PDF """

    f = np.linspace(0, 196.608/2, 4096)
    font = {'size'   : 12}
    matplotlib.rc('font', **font)

    # Create the PdfPages object to which we will save the pages:
    # The with statement makes sure that the PdfPages object is closed properly at
    # the end of the block, even if an Exception occurs.
    pdf = PdfPages(fpath)
    for ii in range(256):
        plt.figure(ii, figsize=(12, 8))
        print "Plotting page %i of 256"%(ii+1)
        ant_id = ii + 1

        plt.plot(f, sp["%iA"%ant_id], c='#000000', alpha=0.7, label='%iA'%ant_id)
        plt.plot(f, sp["%iB"%ant_id], c='#cc0000', alpha=0.7, label='%iB'%ant_id)

        plt.ylim(40, 120)
        plt.title("Stand %i"%ant_id)
        plt.xlabel("Frequency [MHz]")
        plt.ylabel("Power [dB]")
        plt.minorticks_on()
        plt.tight_layout()
        plt.legend(frameon=False)
        #plt.savefig("ant-report/ant-%i.pdf"%(ii+1))
        pdf.savefig()
        plt.close()


    # We can also set the file's metadata via the PdfPages object:
    d = pdf.infodict()
    d['Title'] = 'LEDA Antenna Report'
    d['Author'] = u'LEDA-512'
    d['Subject'] = 'Antenna spectrum report for LEDA-512'
    d['Keywords'] = 'Antenna spectrum report LEDA'
    d['CreationDate'] = datetime.today()
    d['ModDate'] = datetime.today()
    pdf.close()


if __name__ == '__main__':

    sp = snap_spec_all()
    now = datetime.now()

    ant_dir = config.ant_report_dir
    hkl_str = now.strftime("ant_report-%Y-%m-%d_%H-%M-%S.hkl")
    pdf_str = now.strftime("ant_report-%Y-%m-%d_%H-%M-%S.pdf")

    hkl.dump(sp, os.path.join(ant_dir, hkl_str))
    hkl.dump(sp, os.path.join(ant_dir, "ant_report.hkl"))

    print os.path.join(ant_dir, pdf_str)
    ant_report(sp, os.path.join(ant_dir, pdf_str))

    shutil.copy2(os.path.join(ant_dir, pdf_str),
                 os.path.join(ant_dir, 'ant_report.pdf'))

