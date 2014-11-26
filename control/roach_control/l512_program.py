#!/usr/bin/env python
"""
l512_program_4t.py
------------------

Program spectrometers with leda 512 firmware.
"""

import subprocess
from multiprocessing import Process, JoinableQueue, Array

from leda_config import roach_config as config

def progdev_adc16(roach, q, boffile, gain):
    """ Run subprocess to reprogram and calibrate ADC """
    reg_gain = '0x2a=0x%i%i%i%i'%(gain, gain, gain, gain)
    sp = subprocess.Popen(["adc16_init.rb", roach, boffile, '-r', reg_gain], stdout=subprocess.PIPE)
    out, err = sp.communicate()
    q.put(out)
    return

def progdev_all(bofdict, gain, verbose=True):
    """ Initialize all roach boards with boffile and gain settings """

    if isinstance(bofdict, dict):
        roachlist = bofdict.keys()
        boffiles  = [bofdict[k] for k in roachlist]
    else:
        roachlist =  ['rofl%i'%i for i in range(1, 16 + 1)]
        boffiles  = [bofdict for i in range(1, 16 + 1)]
    n_roach = len(roachlist)

    print "Programming all roaches with %s" % boffiles[0]
    print "Gain value: %ix" % gain
    print "Please wait..."
    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for i in range(n_roach):
        p = Process(target=progdev_adc16, args=(roachlist[i], q, boffiles[i], gain))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads
    for p in procs:
        p.join()

    # Print messages
    while q.empty() is False:
        qo = q.get()
        if verbose:
            print q.get()
    print "OK"

if __name__ == '__main__':

    bofdict  = config.bofdict
    gain     = config.gain

    progdev_all(bofdict, gain)

