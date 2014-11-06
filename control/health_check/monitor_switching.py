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

def get_state(rms):
    """0:  cold
       1:  hot
       2:  sky
       -1: too low
       -2: too high
    """
    # TODO: Tune these!
    if rms < 4:
        return -1
    elif rms < 12:
        return 0
    elif rms < 24:
        return 1
    elif rms < 64:
        return 2
    else:
        return -2

def display_switching():
    inputs  = [496, 499, 500, 503, 504, 507, 508, 511]
    ## HACK TESTING
    #inputs = [inp - 1 for inp in inputs]
    roachnum = 15
    roachname = "rofl"+str(roachnum+1)
    samples = get_adc_samples(roachname)
    samples = samples.reshape((samples.shape[0],32))
    rms = [samples[:,inp-32*roachnum].std() for inp in inputs]
    #rms_str = [str(x) for x in rms]
    states  = [get_state(r) for r in rms]
    #symbol_table = "chs*0"
    symbol_table = ['COLD', 'HOT', 'SKY', 'HIGH', 'OFF']
    symbols = [symbol_table[s] for s in states]
    print '\t'.join(symbols)

def monitor_switching():
    now   = time.time()
    start = math.ceil(now) + 0.5
    time.sleep(start - now)
    periodic = PeriodicTimer(1.0, display_switching)
    periodic.start()

if __name__ == "__main__":
    # TODO: Tune the state levels above
    print "WARNING: This script has not yet been tuned properly!"
    monitor_switching()
    # Note: This is how long to run for before exiting
    time.sleep(60)
