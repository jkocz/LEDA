#!/usr/bin/env python

import numpy as np
import subprocess
import threading, time
import math
import matplotlib.pyplot as plt

def get_adc_samples(roach, nsamps=1024):
    nstands = 16 # Not changeable
    npols   = 2  # Not changeable
    #nsamps  = 256#1024
    #return 40 * np.random.standard_normal((nsamps, nstands, npols))                                                                                                        
    sp = subprocess.Popen(["adc16_dump_chans.rb", "-l", str(nsamps), roach],
                          stdout=subprocess.PIPE)
    out, err = sp.communicate()
    if len(out) < 1024:
        print "ERROR adc16_dump_chans.rb output:\n---"
        print out
        print "---"
    data = np.fromstring(out, sep=' ', dtype='int')
    try:
        data = data.reshape(nsamps, nstands, npols)
    except ValueError:
        return None
    return data

def get_input_samples(i, nsamps=1024):
    roachnum = i / 32
    j = i % 32 / 2
    p = i % 32 % 2
    samples = get_adc_samples("rofl"+str(roachnum+1), nsamps)
    return samples[:,j,p]

class PeriodicTimer(object):
    def __init__(self, interval_secs, callback):
        self.secs = interval_secs
        self.callback = callback
        self.timerThread = threading.Thread(target=self.threadFunc)
        self.timerThread.daemon = True
    def start(self):
        self.timerThread.start()
    def threadFunc(self):
        next_call = time.time()
        while True:
            self.callback()
            next_call = next_call + self.secs
            if next_call > time.time():
                time.sleep(next_call - time.time())
            else:
                print "Warning: Callback was too slow"

if __name__ == "__main__":
    import sys
    if len(sys.argv) <= 1:
        print "Usage:", sys.argv[0], "1-512"
        sys.exit(0)
    inp = int(sys.argv[1]) - 1
    if inp < 0 or inp > 511:
        print "Invalid input index"
        sys.exit(-1)
    
    def print_rms():
        samples = get_input_samples(inp)
        spec = (np.abs(np.fft.rfft(samples))**2)[:-1]
        smallspec = spec.reshape((spec.shape[0]/32,32)).sum(axis=1)
        smallspec = 10*np.log10(smallspec)
        print smallspec.min(), smallspec.max()
        #smallspec = (smallspec - smallspec.min()) / (smallspec.max() - smallspec.min()) * 64
        vmin = 45
        vmax = 95
        n = 32
        smallspec = (smallspec - vmin) / (vmax - vmin) * n
        smallspec[smallspec<0]  = 0
        smallspec[smallspec>=n] = n
        #print spec.reshape((spec.shape[0]/16,16)).sum(axis=1)[4]
        print '+'*64
        for x in smallspec:
            print '='*int(x+0.5)
        #rms = samples.std()
        #print "%02i%s" % (int(rms+0.5), int(rms+0.5) * "-")
    now   = time.time()
    start = math.ceil(now) + 0.5
    time.sleep(start - now)
    p = PeriodicTimer(1.0, print_rms)
    p.start()
    """
    samples = get_input_samples(inp, 1024)
    spec = (np.abs(np.fft.rfft(samples))**2)[:-1]
    smallspec = spec.reshape((spec.shape[0]/8,8)).sum(axis=1)
    print smallspec
    for x in smallspec:
        print '='*x
    """
    ##plt.plot(10*np.log10(spec))
    #plt.plot(10*np.log10(smallspec))
    #plt.show()
    
    # Note: This is how long to run for before exiting
    time.sleep(60)
    """
    #running = True
    #print 14 * "=" + " 32 " + 14 * "="
    #print "32" + 32*"="
    #while running:
    nreps = 120#480
    for r in xrange(nreps):
        #samples = get_adc_samples("rofl"+str(roachnum+1))
        #rms = samples[:,j,p].std()
        rms = get_input_samples(inp).std()
        #print int(rms) * "-"
        print "%02i%s" % (int(rms), int(rms) * "-")
        time.sleep(1.0)
    """
