#!/usr/bin/env python
""" adc16_initall.py - reprogram all ROACH boards

Reprogram all roach boards using the adc16_init.rb script, which performs SERDES calibration
after FPGA reprogramming. This script adds multiple subprocesses so that reprogramming is much
quicker than stepping through one by one.
"""
from multiprocessing import Process, JoinableQueue
import subprocess
import time, sys, os

def progdev_adc16(roach, q, boffile, gain):
    """ Run subprocess to reprogram and calibrate ADC """
    reg_gain = '0x2a=0x%i%i%i%i'%(gain, gain, gain, gain)
    sp = subprocess.Popen(["adc16_init.rb", roach, boffile, '-r', reg_gain], stdout=subprocess.PIPE)
    out, err = sp.communicate()
    q.put(out)
    return

def progdev_all(boffile, gain):
    """ Initialize all roach boards with boffile and gain settings """
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach = len(roachlist)
    
    print "Programming all roaches with %s"%boffile
    print "Gain value: %ix"%gain
    print "Please wait..."
    # Create threads and message queue
    procs = []
    q     = JoinableQueue()
    for i in range(n_roach):
        p = Process(target=progdev_adc16, args=(roachlist[i], q, boffile, gain))
        procs.append(p)
    # Start threads
    for p in procs:
        p.start()
    # Join threads      
    for p in procs:
        p.join()
    
    # Print messages
    while q.empty() is False:
        print q.get()
    print "OK"
    
if __name__ == '__main__':
    try:
        boffile = sys.argv[1]
        gain    = int(sys.argv[2])
    except:
        print "Usage: adc16_initall.py boffile_name.bof gain"
        exit()
    
    progdev_all(boffile, gain)
