#!/usr/bin/env python

import numpy as np
import subprocess
import threading, time
import math

def get_adc_samples(roach):
    nstands = 16 # Not changeable
    npols   = 2  # Not changeable
    nsamps  = 256#1024
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

def get_input_samples(i):
    roachnum = i / 32
    j = i % 32 / 2
    p = i % 32 % 2
    samples = get_adc_samples("rofl"+str(roachnum+1))
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
        rms = get_input_samples(inp).std()
        print "%02i%s" % (int(rms), int(rms) * "-")
    now   = time.time()
    start = math.ceil(now) + 0.5
    time.sleep(start - now)
    p = PeriodicTimer(1.0, print_rms)
    p.start()
    
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
