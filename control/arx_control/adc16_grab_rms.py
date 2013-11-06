#!/usr/bin/env python
""" Print ADC RMS values to screen """

__author__     = "LEDA Collaboration"
__version__    = "2.0"
__status__     = "Development"

from multiprocessing import Process, Array
import subprocess
import time
import numpy as np
import ujson as json
from pywt import dwt, idwt
from termcolor import colored, cprint

def grab_adc16(roach, arr):
    """ Run subprocess to call adc16_dump_chans script """
    sp = subprocess.Popen(["adc16_dump_chans.rb", "-l", str(n_samples), roach], stdout=subprocess.PIPE)
    out, err = sp.communicate()
    data = np.fromstring(out, sep=' ', dtype='int')
    for i in range(len(arr)):
        arr[i] = data[i]
    return

if __name__ == '__main__':
    roachlist = ['rofl%i'%i for i in range(1,16+1)]
    n_roach, n_samples = len(roachlist), 1024
    
    allsystemsgo = True
    while allsystemsgo:
        # Create threads and shared memory
        procs = []
        arrs  = [Array('i', range(n_samples*32)) for roach in roachlist]
        for i in range(n_roach):
            p = Process(target=grab_adc16, args=(roachlist[i], arrs[i]))
            procs.append(p)
        # Start threads
        for p in procs:
            p.start()
        # Join threads      
        for p in procs:
            p.join()
            
        data = np.zeros([n_roach*32, n_samples])
        
        for i in range(len(arrs)):
            a = np.array(arrs[i][:]).reshape([n_samples, 32]).T
            data[32*i:32*i+32] = a 
        
        i = 1
        squares = []
        for row in data:
            rms = np.average(np.abs(data[i-1]))
            if rms <= 1.0:
                cprint("%03d\t%02.2f\tNO_POW"%(i, rms), 'red')
            elif rms <= 8.0:
                cprint("%03d\t%02.2f\tLOW_POW"%(i, rms), 'yellow')
            else:
                cprint("%03d\t%02.2f\tOK"%(i, rms), 'green')
            i += 1
        
        exit()