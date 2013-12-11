#!/usr/bin/env python
""" 
roach_check.py

Establishes connections to all roach boards and queries board clock.
"""
from corr import katcp_wrapper
import time
from threading import Thread
from Queue import Queue

def roach_tester(i, q, p=7147):
    """ Worker thread that tests roach boards
    
    Arguments:
    i (int) Thread ID
    q (queue): Queue
    """
    while True:
        try:
            r = q.get()
            fpga = katcp_wrapper.FpgaClient(r, p)
            time.sleep(0.01)
            if fpga.is_connected():
                clk = fpga.est_brd_clk()
                print "%s: %s MHz"%(r, clk)
            else:
                print "Error: cannot connect to %s"%r
            fpga.stop()
        except:
            print "Error: cannot connect to %s"%r
        q.task_done()

if __name__ == '__main__':
    print "Running ROACH board clock check on all ROACH boards"
    print "Nb: clock is estimation only."
    roaches = ['rofl%i'%ii for ii in range(1,16+1)]
    
    #Spawn thread pool
    num_threads = 16
    queue = Queue()
    for i in range(num_threads):
        worker = Thread(target=roach_tester, args=(i, queue))
        worker.setDaemon(True)
        worker.start()
    #Place work in queue
    for r in roaches:
        queue.put(r)
    #Wait until worker threads are done to exit    
    queue.join()
    
    print "Done."
